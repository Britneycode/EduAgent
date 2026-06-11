# 异步数据库迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端从同步 SQLite 升级为异步双模（开发 aiosqlite / 生产 asyncpg），Service 层全面异步化，引入 Alembic 迁移框架。

**Architecture:** 数据库层改用 `create_async_engine` + `async_sessionmaker`，通过 DATABASE_URL scheme 自动切换 SQLite/PostgreSQL。Service 层所有方法改为 `async def`，DB 操作用 `await session.execute(select(...))`。Wiki/RAG 的 CPU 密集型操作用 `asyncio.to_thread()` 包装。

**Tech Stack:** SQLAlchemy 2.0 async, asyncpg, aiosqlite, Alembic (async mode), pytest-asyncio

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `pyproject.toml` | 添加 asyncpg, aiosqlite, alembic, pytest-asyncio 依赖 |
| 重写 | `app/core/database.py` | 异步引擎 + async_sessionmaker + async get_db |
| 修改 | `app/core/config.py` | 默认 DATABASE_URL 改为 `sqlite+aiosqlite://` |
| 重写 | `app/services/chat_service.py` | 所有方法改 async，查询改 select() |
| 重写 | `app/services/profile_service.py` | 所有方法改 async，查询改 select() |
| 修改 | `app/wiki/wiki_service.py` | write_back 改 async |
| 修改 | `app/wiki/rag_engine.py` | search/build_context 改 async + to_thread |
| 修改 | `app/wiki/__init__.py` | init_wiki 改 async，get_wiki_service 接收 AsyncSession |
| 修改 | `app/wiki/ingestion.py` | ingest_course 改 async |
| 修改 | `app/agents/orchestrator.py` | Service 调用加 await |
| 修改 | `app/api/chat.py` | stream 端点改用 AsyncSessionLocal |
| 修改 | `app/api/profile.py` | Session → AsyncSession |
| 修改 | `app/api/wiki.py` | Session → AsyncSession |
| 重写 | `app/main.py` | lifespan 改 async init |
| 创建 | `alembic.ini` | Alembic 配置 |
| 创建 | `alembic/env.py` | 异步迁移环境 |
| 创建 | `alembic/script.py.mako` | 迁移脚本模板 |
| 创建 | `alembic/versions/0001_initial_schema.py` | 初始迁移 |
| 修改 | `tests/conftest.py` | 异步测试 fixture |

---

### Task 1: 添加依赖

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 添加异步数据库和迁移依赖**

在 `pyproject.toml` 的 `dependencies` 列表中添加：

```toml
dependencies = [
    "fastapi[standard]>=0.115.0",
    "httpx>=0.28.0",
    "pydantic-settings>=2.7.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "aiosqlite>=0.21.0",
    "alembic>=1.15.0",
    "numpy>=2.0.0",
    "sentence-transformers>=3.3.0",
]
```

在 `[dependency-groups]` 的 `dev` 组中添加：

```toml
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
]
```

- [ ] **Step 2: 安装依赖**

Run: `cd backend && uv sync`
Expected: 依赖安装成功，无报错

- [ ] **Step 3: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore: 添加 asyncpg, aiosqlite, alembic, pytest-asyncio 依赖"
```

---

### Task 2: 重写数据库层

**Files:**
- Modify: `backend/app/core/config.py`
- Rewrite: `backend/app/core/database.py`
- Test: `backend/tests/test_database.py`

- [ ] **Step 1: 写测试 — 验证异步引擎和会话**

创建 `backend/tests/test_database.py`：

```python
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine, get_db


@pytest.mark.asyncio
async def test_engine_is_async():
    """引擎应该是异步的。"""
    assert "async" in type(engine).__module__


@pytest.mark.asyncio
async def test_session_is_async():
    """get_db 应该产出 AsyncSession。"""
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_session_auto_closes():
    """会话在 get_db 退出后应该关闭。"""
    session_ref = None
    async for session in get_db():
        session_ref = session
    assert session_ref is not None
    assert session_ref.is_active is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_database.py -v`
Expected: FAIL — 当前 database.py 没有 AsyncSessionLocal 和异步 engine

- [ ] **Step 3: 修改 config.py 默认 DATABASE_URL**

将 `app/core/config.py` 第 11 行：
```python
database_url: str = "sqlite:///./eduagent.db"
```
改为：
```python
database_url: str = "sqlite+aiosqlite:///./eduagent.db"
```

- [ ] **Step 4: 重写 database.py**

将 `app/core/database.py` 完整替换为：

```python
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类。"""


settings = get_settings()
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：提供异步数据库会话，请求结束后自动关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """初始化数据库并创建所有已注册的数据表。"""
    from app.models import chat, profile, resource, wiki  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 5: 创建 pytest 配置**

创建 `backend/tests/conftest.py`（如果不存在则创建，存在则合并）：

```python
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture
async def async_session():
    """提供测试用异步内存数据库会话。"""
    test_engine = create_async_engine(TEST_DATABASE_URL)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
```

在 `backend/pyproject.toml` 中添加 pytest-asyncio 配置：

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_database.py -v`
Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/database.py backend/app/core/config.py backend/tests/test_database.py backend/tests/conftest.py backend/pyproject.toml
git commit -m "feat: 数据库层改为异步引擎 (AsyncSession + create_async_engine)"
```

---

### Task 3: ChatService 异步化

**Files:**
- Rewrite: `backend/app/services/chat_service.py`
- Test: `backend/tests/test_services/test_chat_service.py`

- [ ] **Step 1: 写测试 — 验证异步 ChatService**

创建 `backend/tests/test_services/test_chat_service.py`：

```python
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession, ChatMessage
from app.models.resource import GeneratedResource
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_create_session(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session()
    assert isinstance(session_id, int)
    assert session_id > 0


@pytest.mark.asyncio
async def test_session_exists(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session()
    assert await service.session_exists(session_id) is True
    assert await service.session_exists(99999) is False


@pytest.mark.asyncio
async def test_save_and_list_messages(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session()
    msg = await service.save_message(session_id, "user", "你好")
    assert msg.role == "user"
    assert msg.content == "你好"
    messages = await service.list_messages(session_id)
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_save_and_list_resources(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session()
    resource = await service.save_resource(
        session_id=session_id,
        resource_type="document",
        title="测试文档",
        content="内容",
    )
    assert resource.id is not None
    resources = await service.list_resources(session_id)
    assert len(resources) == 1


@pytest.mark.asyncio
async def test_list_sessions(async_session: AsyncSession):
    service = ChatService(session=async_session)
    await service.create_session("会话A")
    await service.create_session("会话B")
    sessions = await service.list_sessions()
    assert len(sessions) == 2


@pytest.mark.asyncio
async def test_update_session_title(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session("旧标题")
    await service.update_session_title(session_id, "新标题")
    session = await service.get_session(session_id)
    assert session is not None
    assert session.title == "新标题"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_chat_service.py -v`
Expected: FAIL — ChatService 方法还是同步的

- [ ] **Step 3: 重写 ChatService**

将 `backend/app/services/chat_service.py` 完整替换为：

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.resource import GeneratedResource


class ChatService:
    """聊天会话与资源持久化服务。"""

    def __init__(self, session: AsyncSession | None) -> None:
        self.session = session
        self._resource_id_seq = 1

    async def create_session(self, title: str = "新学习会话") -> int:
        chat_session = ChatSession(title=title)
        self._require_session().add(chat_session)
        await self._require_session().commit()
        await self._require_session().refresh(chat_session)
        return chat_session.id

    async def session_exists(self, session_id: int) -> bool:
        if self.session is None:
            return True
        result = await self._require_session().execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalars().first() is not None

    async def save_message(
        self,
        session_id: int,
        role: str,
        content: str,
        message_type: str = "text",
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            message_type=message_type,
        )
        self._require_session().add(message)
        await self._require_session().commit()
        await self._require_session().refresh(message)
        return message

    async def list_sessions(self) -> list[ChatSession]:
        result = await self._require_session().execute(
            select(ChatSession).order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_session(self, session_id: int) -> ChatSession | None:
        result = await self._require_session().execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalars().first()

    async def update_session_title(self, session_id: int, title: str) -> None:
        session = await self.get_session(session_id)
        if session is not None:
            session.title = title
            await self._require_session().commit()

    async def list_messages(self, session_id: int) -> list[ChatMessage]:
        result = await self._require_session().execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
        return list(result.scalars().all())

    async def list_resources(self, session_id: int) -> list[GeneratedResource]:
        result = await self._require_session().execute(
            select(GeneratedResource)
            .where(GeneratedResource.session_id == session_id)
            .order_by(GeneratedResource.id.asc())
        )
        return list(result.scalars().all())

    async def save_resource(
        self,
        session_id: int,
        resource_type: str,
        title: str,
        content: str,
        knowledge_point: str | None = None,
        agent_name: str | None = None,
    ) -> GeneratedResource:
        if self.session is None:
            resource = GeneratedResource(
                id=self._resource_id_seq,
                session_id=session_id,
                resource_type=resource_type,
                title=title,
                content=content,
                knowledge_point=knowledge_point,
                agent_name=agent_name,
            )
            self._resource_id_seq += 1
            return resource

        resource = GeneratedResource(
            session_id=session_id,
            resource_type=resource_type,
            title=title,
            content=content,
            knowledge_point=knowledge_point,
            agent_name=agent_name,
        )
        self._require_session().add(resource)
        await self._require_session().commit()
        await self._require_session().refresh(resource)
        return resource

    def _require_session(self) -> AsyncSession:
        if self.session is None:
            raise ValueError("ChatService 需要有效的数据库会话")
        return self.session
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_chat_service.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/chat_service.py backend/tests/test_services/test_chat_service.py
git commit -m "feat: ChatService 全面异步化"
```

---

### Task 4: ProfileService 异步化

**Files:**
- Rewrite: `backend/app/services/profile_service.py`
- Test: `backend/tests/test_services/test_profile_service.py`

- [ ] **Step 1: 写测试 — 验证异步 ProfileService**

创建 `backend/tests/test_services/test_profile_service.py`：

```python
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.profile_service import ProfileService, DEFAULT_USER_ID


@pytest.mark.asyncio
async def test_get_or_create_profile(async_session: AsyncSession):
    service = ProfileService(session=async_session)
    profile = await service.get_or_create_profile(session_id=1)
    assert profile.user_id == DEFAULT_USER_ID
    assert profile.session_id == 1


@pytest.mark.asyncio
async def test_save_profile_update(async_session: AsyncSession):
    service = ProfileService(session=async_session)
    await service.get_or_create_profile(session_id=1)
    updated = await service.save_profile_update(
        session_id=1,
        update={"major": "计算机科学", "grade": "大三"},
    )
    assert updated.major == "计算机科学"
    assert updated.grade == "大三"


@pytest.mark.asyncio
async def test_profile_merge_accumulates(async_session: AsyncSession):
    service = ProfileService(session=async_session)
    await service.get_or_create_profile(session_id=1)
    await service.save_profile_update(1, {"major": "计算机"})
    result = await service.save_profile_update(1, {"grade": "大二"})
    assert result.major == "计算机"
    assert result.grade == "大二"


@pytest.mark.asyncio
async def test_merge_profile_logic():
    service = ProfileService(session=None)
    existing = {"major": "数学", "grade": None, "knowledge_base": {}, "weak_points": []}
    update = {"grade": "大一", "weak_points": ["线性代数"]}
    merged = service.merge_profile(existing, update)
    assert merged["major"] == "数学"
    assert merged["grade"] == "大一"
    assert merged["weak_points"] == ["线性代数"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_profile_service.py -v`
Expected: FAIL

- [ ] **Step 3: 重写 ProfileService**

将 `backend/app/services/profile_service.py` 中所有 DB 操作方法改为 async。核心改动模式：

- `__init__` 参数类型：`Session | None` → `AsyncSession | None`
- `self._require_session().query(M).filter(...)` → `await self._require_session().execute(select(M).where(...))`
- `self._require_session().commit()` → `await self._require_session().commit()`
- `self._require_session().refresh(obj)` → `await self._require_session().refresh(obj)`
- `self._require_session().flush()` → `await self._require_session().flush()`
- 返回类型：`.one_or_none()` → `result.scalars().first()`
- `_require_session` 返回类型改为 `AsyncSession`

需要改为 async 的方法：`get_or_create_profile`, `save_profile_update`, `_get_profile_by_user`

保持同步的方法（纯内存计算）：`merge_profile`, `sanitize_profile_update`, `_to_response`, `_model_to_dict`, `_apply_to_model`, `_normalize_profile_model`, `_normalize_agent_field_value`, `_normalize_field_value`

导入变更：
```python
# 移除
from sqlalchemy.orm import Session
# 添加
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_profile_service.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/profile_service.py backend/tests/test_services/test_profile_service.py
git commit -m "feat: ProfileService 全面异步化"
```

---

### Task 5: WikiService + RAG 层异步化

**Files:**
- Modify: `backend/app/wiki/rag_engine.py`
- Modify: `backend/app/wiki/wiki_service.py`
- Modify: `backend/app/wiki/ingestion.py`
- Modify: `backend/app/wiki/__init__.py`
- Test: `backend/tests/test_wiki_async.py`

- [ ] **Step 1: 写测试 — 验证异步 RAG 和 WikiService**

创建 `backend/tests/test_wiki_async.py`：

```python
from __future__ import annotations

import pytest

from app.wiki.embeddings import DevEmbedding
from app.wiki.graph import KnowledgeGraph
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore
from app.wiki.wiki_service import WikiService


@pytest.fixture
def wiki_service():
    embedding = DevEmbedding()
    vs = VectorStore(embedding_client=embedding, persist_directory=None)
    vs.add(
        chunk_ids=["c1"],
        documents=["神经网络是一种模拟人脑的计算模型"],
        metadatas=[{"title": "神经网络", "chapter": "ch3", "section": "s1"}],
    )
    rag = RAGEngine(vector_store=vs)
    graph = KnowledgeGraph()
    return WikiService(rag_engine=rag, knowledge_graph=graph, vector_store=vs)


@pytest.mark.asyncio
async def test_rag_search_is_async(wiki_service: WikiService):
    results = await wiki_service.search("神经网络")
    assert len(results) > 0
    assert results[0].title == "神经网络"


@pytest.mark.asyncio
async def test_build_context_is_async(wiki_service: WikiService):
    context = await wiki_service.build_context("神经网络")
    assert "神经网络" in context


@pytest.mark.asyncio
async def test_write_back_without_db(wiki_service: WikiService):
    chunk_id = await wiki_service.write_back(
        title="测试回写",
        content="测试内容",
        source_agent="TestAgent",
    )
    assert chunk_id is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_wiki_async.py -v`
Expected: FAIL — search/build_context/write_back 还是同步的

- [ ] **Step 3: 改造 rag_engine.py**

在 `backend/app/wiki/rag_engine.py` 中：

添加导入：
```python
import asyncio
```

将 `search` 方法改为：
```python
async def search(
    self,
    query: str,
    top_k: int = 5,
    chapter: str | None = None,
    min_score: float = 0.0,
) -> list[SearchResult]:
    """语义检索，返回排序后的结果列表。"""
    where = {"chapter": chapter} if chapter else None
    raw_results = await asyncio.to_thread(
        self._vector_store.search, query=query, top_k=top_k, where=where
    )
    # ... 后续处理逻辑不变
```

将 `build_context` 方法改为：
```python
async def build_context(
    self,
    query: str,
    top_k: int = 3,
    chapter: str | None = None,
) -> str:
    results = await self.search(query=query, top_k=top_k, chapter=chapter)
    # ... 后续格式化逻辑不变
```

- [ ] **Step 4: 改造 wiki_service.py**

导入变更：
```python
# 移除
from sqlalchemy.orm import Session
# 添加
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
```

构造函数 `session` 参数类型改为 `AsyncSession | None`。

将 `search` 改为：
```python
async def search(self, query: str, top_k: int = 5, chapter: str | None = None) -> list[SearchResult]:
    return await self._rag_engine.search(query=query, top_k=top_k, chapter=chapter)
```

将 `build_context` 改为：
```python
async def build_context(self, query: str, top_k: int = 3, chapter: str | None = None) -> str:
    return await self._rag_engine.build_context(query=query, top_k=top_k, chapter=chapter)
```

将 `write_back` 改为 async，向量写入用 `await asyncio.to_thread()`，DB 写入用 `await`：
```python
async def write_back(self, title: str, content: str, source_agent: str, ...) -> str | None:
    chunk_id = f"agent_{source_agent}_{title}"
    try:
        await asyncio.to_thread(
            self._vector_store.add,
            chunk_ids=[chunk_id],
            documents=[f"{title}\n\n{content}"],
            metadatas=[{...}],
        )
    except Exception:
        logger.exception("回写向量存储失败: %s", title)
        return None

    if self._session is not None:
        try:
            entry = WikiEntry(...)
            self._session.add(entry)
            await self._session.commit()
        except Exception:
            logger.exception("回写数据库失败: %s", title)

    return chunk_id
```

`get_prerequisites`, `get_knowledge_tree`, `get_related` 保持同步（纯内存图操作）。

- [ ] **Step 5: 改造 wiki/__init__.py**

将 `init_wiki` 改为 `async def init_wiki(session: AsyncSession | None = None)`。

将 `get_wiki_service` 的 `session` 参数类型改为 `AsyncSession | None`。

如果 `init_wiki` 内部调用 `ingest_course`，也需要 `await`。

- [ ] **Step 6: 改造 wiki/ingestion.py**

将 `ingest_course` 改为 `async def`，DB 操作加 `await`，向量写入用 `await asyncio.to_thread()`。

- [ ] **Step 7: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_wiki_async.py -v`
Expected: 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/wiki/rag_engine.py backend/app/wiki/wiki_service.py backend/app/wiki/__init__.py backend/app/wiki/ingestion.py backend/tests/test_wiki_async.py
git commit -m "feat: Wiki/RAG 层异步化，CPU 密集操作用 to_thread 包装"
```

---

### Task 6: Orchestrator + API 层适配

**Files:**
- Modify: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/api/profile.py`
- Modify: `backend/app/api/wiki.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 改造 orchestrator.py**

所有 Service 调用加 `await`。具体改动：

```python
# 第 58 行附近 — route 是同步的，不需要 await
decision = self.router_agent.route(user_message)

# 第 70 行附近 — extract_profile_update 是同步的
update = self.profile_agent.extract_profile_update(user_message)

# 第 76-80 行 — save_profile_update 改为 await
profile_resp = await self.profile_service.save_profile_update(...)

# 第 86-90 行 — get_or_create_profile 改为 await
profile_resp = await self.profile_service.get_or_create_profile(...)

# 第 138-146 行 — save_resource 改为 await
resource_model = await self.chat_service.save_resource(...)

# 第 166-170 行 — save_message 改为 await
await self.chat_service.save_message(...)

# 第 176 行 — get_session 改为 await
session_obj = await self.chat_service.get_session(session_id)

# 第 179 行 — update_session_title 改为 await
await self.chat_service.update_session_title(session_id, title)
```

同时，Agent 的 `_build_wiki_context` 方法在 DocAgent/QuizAgent/CodeAgent 中调用了 `wiki_service.build_context`，现在是 async 了。需要将 `_build_wiki_context` 改为 `async def`，并在 `generate_*` 方法中 `await` 调用。

涉及文件：
- `backend/app/agents/doc_agent.py` — `_build_wiki_context` 不存在，wiki 调用在 `generate_document` 中直接调用，改为 `await self.wiki_service.build_context(...)`
- `backend/app/agents/quiz_agent.py` — `_build_wiki_context` 改为 `async def`
- `backend/app/agents/code_agent.py` — `_build_wiki_context` 改为 `async def`

- [ ] **Step 2: 改造 API 层**

`backend/app/api/chat.py`：
- 导入变更：`from sqlalchemy.ext.asyncio import AsyncSession` 替换 `from sqlalchemy.orm import Session`
- `from app.core.database import AsyncSessionLocal, get_db` 替换 `from app.core.database import SessionLocal, get_db`
- `build_orchestrator` 参数类型改为 `AsyncSession`
- `get_wiki_service(session=db_session)` 不变（已在 Task 5 中改了参数类型）
- stream 端点中 `db = SessionLocal()` 改为 `async with AsyncSessionLocal() as db:`
- 所有 `chat_service.xxx()` 调用加 `await`

`backend/app/api/profile.py`：
- `Session` → `AsyncSession`
- `get_db` 已经是 async 版本
- Service 调用加 `await`

`backend/app/api/wiki.py`：
- `Session` → `AsyncSession`
- `wiki.search(...)` 等调用加 `await`

- [ ] **Step 3: 改造 main.py**

```python
from app.core.database import AsyncSessionLocal, init_db

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.wiki import init_wiki

    await init_db()

    async with AsyncSessionLocal() as session:
        await init_wiki(session=session)

    yield
```

移除 `SessionLocal` 导入。

- [ ] **Step 4: 运行全部测试**

Run: `cd backend && uv run pytest -v`
Expected: 所有测试通过

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/ backend/app/api/ backend/app/main.py
git commit -m "feat: Orchestrator + API + main.py 适配异步数据库层"
```

---

### Task 7: Alembic 迁移框架

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (目录)

- [ ] **Step 1: 初始化 Alembic**

Run: `cd backend && uv run alembic init -t async alembic`
Expected: 创建 `alembic/` 目录和 `alembic.ini`

- [ ] **Step 2: 配置 alembic/env.py**

修改 `backend/alembic/env.py`，设置 `target_metadata` 和数据库 URL：

在文件顶部添加：
```python
from app.core.config import get_settings
from app.core.database import Base
from app.models import chat, profile, resource, wiki  # noqa: F401
```

设置：
```python
target_metadata = Base.metadata
```

在 `run_async_migrations` 函数中，将 `config.get_main_option("sqlalchemy.url")` 替换为：
```python
settings = get_settings()
connectable = create_async_engine(settings.database_url)
```

- [ ] **Step 3: 生成初始迁移**

Run: `cd backend && uv run alembic revision --autogenerate -m "初始 schema"`
Expected: 在 `alembic/versions/` 下生成迁移文件，包含 5 张表的 create_table

- [ ] **Step 4: 验证迁移可执行**

先删除旧数据库：
Run: `rm -f backend/eduagent.db`

运行迁移：
Run: `cd backend && uv run alembic upgrade head`
Expected: 成功创建所有表

- [ ] **Step 5: 运行全部测试确认无回归**

Run: `cd backend && uv run pytest -v`
Expected: 所有测试通过

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: 引入 Alembic 异步迁移框架，生成初始 schema"
```

---

### Task 8: 端到端验证

**Files:**
- Test: `backend/tests/test_api/test_chat_api.py`

- [ ] **Step 1: 写端到端 API 测试**

创建 `backend/tests/test_api/test_chat_api.py`：

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_session_and_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat/session")
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
        assert session_id > 0

        resp = await client.get("/api/chat/sessions")
        assert resp.status_code == 200
        sessions = resp.json()
        assert any(s["id"] == session_id for s in sessions)


@pytest.mark.asyncio
async def test_stream_chat():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat/stream",
            json={"message": "你好"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert len(resp.text) > 0
```

- [ ] **Step 2: 运行端到端测试**

Run: `cd backend && uv run pytest tests/test_api/test_chat_api.py -v`
Expected: 3 tests PASS

- [ ] **Step 3: 运行全部测试确认无回归**

Run: `cd backend && uv run pytest -v`
Expected: 所有测试通过

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_api/test_chat_api.py
git commit -m "test: 添加异步 API 端到端测试"
```
