# 异步数据库迁移设计 — SQLite/PostgreSQL 双模 + Service 层异步化

**日期**：2026-04-18
**范围**：后端基础设施第一批升级
**目标**：将同步 SQLite 架构升级为异步双模（开发 aiosqlite / 生产 asyncpg），Service 层全面异步化，引入 Alembic 迁移框架

---

## 1. 背景与动机

当前后端使用同步 SQLAlchemy + SQLite，存在三个核心问题：

1. **事件循环阻塞**：FastAPI 路由是 async，但 Service 层全部 sync，DB 操作阻塞事件循环
2. **生产不可用**：SQLite 不支持并发写入，无法承载多用户场景
3. **无迁移管理**：使用 `create_all` 建表，无法做增量 schema 变更

## 2. 方案概述

采用渐进式迁移，通过 DATABASE_URL 配置自动切换：

- `sqlite+aiosqlite:///./eduagent.db` → 开发环境，零配置
- `postgresql+asyncpg://user:pass@host/db` → 生产环境

## 3. 详细设计

### 3.1 数据库层 (`core/database.py`)

**改造前**：
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)
```

**改造后**：
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

**关键决策**：
- `expire_on_commit=False`：避免 commit 后访问属性触发隐式 IO
- `get_db` 使用 `async with` 确保会话自动关闭
- 异常时自动 rollback

### 3.2 Service 层异步化

**统一改动模式**：

| 改造前 | 改造后 |
|--------|--------|
| `def method(self):` | `async def method(self):` |
| `self.session.query(M).filter(...)` | `await self.session.execute(select(M).where(...))` |
| `self.session.add(obj)` | `self.session.add(obj)` (不变) |
| `self.session.commit()` | `await self.session.commit()` |
| `self.session.refresh(obj)` | `await self.session.refresh(obj)` |
| 返回 ORM 对象 | `result.scalars().first()` / `.all()` |

**涉及文件**：
- `services/chat_service.py` — 构造函数 `session: AsyncSession`，所有方法 async
- `services/profile_service.py` — 同上
- `wiki/wiki_service.py` — 同上，向量检索用 `asyncio.to_thread()`

### 3.3 Alembic 迁移框架

**初始化**：
```bash
cd backend
uv run alembic init -t async alembic
```

**`alembic/env.py` 关键配置**：
- 使用 `async_engine_from_config` 创建异步引擎
- `target_metadata = Base.metadata`
- `sqlalchemy.url` 从 `app.core.config.get_settings().database_url` 读取

**初始迁移**：
```bash
uv run alembic revision --autogenerate -m "初始 schema"
```

覆盖现有 5 张表：`chat_sessions`, `chat_messages`, `generated_resources`, `student_profiles`, `wiki_entries`

**启动流程变更**：
- 移除 `init_db()` 中的 `Base.metadata.create_all()`
- `main.py` lifespan 中改为 `await run_alembic_upgrade()`（开发模式）或手动执行迁移（生产模式）

### 3.4 Wiki/RAG 层适配

向量存储（Numpy）和 Embedding 是 CPU 密集型，不直接改 async，而是在调用处包装：

```python
# rag_engine.py
async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
    return await asyncio.to_thread(self._sync_search, query, top_k)
```

**涉及文件**：
- `wiki/rag_engine.py` — `search`, `build_context` 改 async
- `wiki/vector_store.py` — 保持同步，被 `to_thread` 调用
- `wiki/embeddings.py` — 保持同步，被 `to_thread` 调用
- `wiki/ingestion.py` — `ingest_course` 改 async（写关系库部分需要 await）
- `wiki/__init__.py` — `init_wiki` 改 async，`get_wiki_service` 接收 `AsyncSession`

### 3.5 Agent 层适配

- Agent 的 `generate_*` 方法已经是 async，无需改动
- `RouterAgent.route()` 和 `ProfileAgent.extract_profile_update()` 是纯 CPU（正则），保持同步
- `Orchestrator.run()` 内部所有 Service 调用加 `await`

### 3.6 API 层适配

- `chat.py`：`get_db` 改为从 `core/database` 导入的 async 版本（已完成）
- stream 端点：`SessionLocal()` 改为 `AsyncSessionLocal()` + `async with`
- 所有 Service 调用加 `await`

### 3.7 `main.py` 生命周期

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_wiki()  # 异步初始化知识库
    yield
```

## 4. 依赖变更

新增到 `pyproject.toml`：
```toml
dependencies = [
    # ... 现有依赖
    "asyncpg>=0.30.0",
    "aiosqlite>=0.21.0",
    "alembic>=1.15.0",
]
```

## 5. 配置变更

`core/config.py` 默认值更新：
```python
database_url: str = "sqlite+aiosqlite:///./eduagent.db"
```

生产环境 `.env`：
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eduagent
```

## 6. 测试策略

- 现有测试改为 `pytest-asyncio`，fixture 提供 `AsyncSession`
- 测试默认使用 `sqlite+aiosqlite://` 内存数据库
- 新增依赖：`pytest-asyncio`

## 7. 不在本次范围

- 认证系统（第二批）
- 向量库替换为 Chroma/Milvus（第二批）
- LangGraph 集成（第三批）
- Media/Tutor Agent（第三批）
- docker-compose.yml（随 PostgreSQL 生产部署一起提供）
- Redis 缓存（第二批）

## 8. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| SQLite 和 PostgreSQL 的 SQL 方言差异 | 使用 SQLAlchemy ORM 抽象，避免原生 SQL |
| 异步改造遗漏同步调用 | 改造后全量运行测试，检查 RuntimeWarning |
| Alembic autogenerate 遗漏变更 | 生成后人工审查迁移脚本 |
| `to_thread` 性能开销 | 仅用于 CPU 密集型操作，IO 操作直接 await |
