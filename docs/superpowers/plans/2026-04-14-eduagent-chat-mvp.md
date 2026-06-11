# EduAgent 对话 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 EduAgent 首个可交付切片：单用户模式下的聊天页 + 画像页闭环，支持真实讯飞星火生成、后端 SSE 流式返回、简化版 Router/Profile/Doc Agent、SQLite 持久化与前后端真实联通。

**Architecture:** 后端使用 FastAPI 提供聊天流式接口与画像查询接口，基于 SQLite + SQLAlchemy 持久化会话、消息、画像与生成资源，使用轻量 orchestrator 串联 RouterAgent、ProfileAgent 与 DocAgent，并统一控制 SSE 事件顺序。前端使用 Next.js App Router 构建聊天页与画像页，通过 fetch + ReadableStream 消费 SSE 事件，展示中文化的流式消息、Agent 状态与资源卡片；LLM 层默认真实接入讯飞星火，缺少凭证或调用失败时只返回中文错误，不伪造内容。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy、Pydantic v2、SQLite、httpx、pytest、pytest-asyncio；Next.js 15、React 19、TypeScript、Tailwind CSS、Vitest、Testing Library、pnpm。

---

## 文件结构与职责映射

### 后端新增文件

- Create: `backend/pyproject.toml` — Python 项目依赖与脚本入口
- Create: `backend/app/__init__.py` — 应用包初始化
- Create: `backend/app/main.py` — FastAPI 入口，注册路由、CORS、启动建表
- Create: `backend/app/core/__init__.py` — core 包初始化
- Create: `backend/app/core/config.py` — 基础配置（数据库路径、CORS、星火凭证）
- Create: `backend/app/core/database.py` — SQLAlchemy engine、session、Base、初始化函数
- Create: `backend/app/core/llm.py` — 统一 LLM 客户端接口与真实讯飞星火客户端
- Create: `backend/app/models/__init__.py` — 模型导出
- Create: `backend/app/models/chat.py` — ChatSession、ChatMessage 模型
- Create: `backend/app/models/profile.py` — StudentProfile 模型
- Create: `backend/app/models/resource.py` — GeneratedResource 模型
- Create: `backend/app/schemas/__init__.py` — schemas 包初始化
- Create: `backend/app/schemas/chat.py` — Chat 请求、SSE 事件、资源数据模型
- Create: `backend/app/schemas/profile.py` — 画像响应模型
- Create: `backend/app/services/__init__.py` — services 包初始化
- Create: `backend/app/services/chat_service.py` — 会话创建/复用、消息保存、资源保存
- Create: `backend/app/services/profile_service.py` — 获取、创建、合并与更新画像
- Create: `backend/app/agents/__init__.py` — agents 包初始化
- Create: `backend/app/agents/router_agent.py` — 请求意图判定
- Create: `backend/app/agents/profile_agent.py` — 从用户文本抽取画像增量
- Create: `backend/app/agents/doc_agent.py` — 基于主题与画像调用真实星火生成个性化学习文档
- Create: `backend/app/agents/orchestrator.py` — 统一事件流编排，严格输出 spec 定义的事件顺序
- Create: `backend/app/api/__init__.py` — API 包初始化
- Create: `backend/app/api/chat.py` — `/api/chat/session` 会话创建接口与 `/api/chat/stream` SSE 接口
- Create: `backend/app/api/profile.py` — `/api/profile` 画像接口
- Create: `backend/tests/conftest.py` — 测试数据库与应用 fixture
- Create: `backend/tests/test_agents/test_router_agent.py` — RouterAgent 测试
- Create: `backend/tests/test_agents/test_profile_agent.py` — ProfileAgent 测试
- Create: `backend/tests/test_agents/test_doc_agent.py` — DocAgent 测试
- Create: `backend/tests/test_agents/test_orchestrator.py` — orchestrator 事件顺序测试
- Create: `backend/tests/test_api/test_chat_api.py` — 聊天 SSE 接口测试
- Create: `backend/tests/test_api/test_profile_api.py` — 画像接口测试
- Create: `backend/tests/test_services/test_profile_service.py` — 画像服务测试
- Create: `backend/tests/test_services/test_chat_service.py` — 聊天服务测试

### 前端新增文件

- Create: `frontend/package.json` — 前端依赖与脚本
- Create: `frontend/tsconfig.json` — TypeScript 配置
- Create: `frontend/next.config.ts` — Next.js 配置
- Create: `frontend/postcss.config.js` — PostCSS 配置
- Create: `frontend/tailwind.config.ts` — Tailwind 主题配置
- Create: `frontend/eslint.config.mjs` — ESLint 配置
- Create: `frontend/vitest.config.ts` — Vitest 测试配置
- Create: `frontend/vitest.setup.ts` — Testing Library 与 jsdom 测试初始化
- Create: `frontend/tests/mocks/handlers.ts` — MSW (Mock Service Worker) API mock handlers
- Create: `frontend/tests/mocks/server.ts` — MSW 测试服务器配置
- Create: `frontend/app/globals.css` — 全局样式与暖色主题变量
- Create: `frontend/app/layout.tsx` — 根布局
- Create: `frontend/app/page.tsx` — 请求后端创建真实会话后跳转到对应聊天页
- Create: `frontend/app/(main)/layout.tsx` — 主区域布局与导航
- Create: `frontend/app/(main)/chat/[sessionId]/page.tsx` — 基于真实 `session_id` 的聊天页
- Create: `frontend/app/(main)/profile/page.tsx` — 通过查询参数读取当前 `session_id` 的画像页
- Create: `frontend/components/chat/ChatMessage.tsx` — 消息组件
- Create: `frontend/components/chat/StreamingText.tsx` — 流式文本组件
- Create: `frontend/components/chat/ResourceCard.tsx` — 资源卡片组件
- Create: `frontend/components/chat/AgentStatus.tsx` — Agent 状态组件
- Create: `frontend/components/profile/ProfileSummary.tsx` — 画像展示组件
- Create: `frontend/lib/api.ts` — REST 请求封装
- Create: `frontend/lib/sse.ts` — SSE 事件消费与解析
- Create: `frontend/lib/types.ts` — 前端类型定义
- Create: `frontend/tests/layout.test.tsx` — 布局测试
- Create: `frontend/tests/sse.test.ts` — SSE 解析测试
- Create: `frontend/tests/chat-components.test.tsx` — 聊天组件测试
- Create: `frontend/tests/chat-page.test.tsx` — 聊天页测试
- Create: `frontend/tests/profile-page.test.tsx` — 画像页测试

### 环境辅助文件

- Create: `backend/.env.example` — 后端示例环境变量（包含 `SPARK_APP_ID`、`SPARK_API_KEY`、`SPARK_API_SECRET`、`SPARK_DEV_MODE`）
- Create: `frontend/.env.example` — 前端示例环境变量
- Modify: `docs/superpowers/specs/2026-04-14-eduagent-chat-mvp-design.md` — 仅在实现中发现规格错误时再更新

---

### Task 1: 初始化后端工程骨架

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/.env.example`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: 写最小健康检查测试**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: FAIL，提示 `app.main` 不存在或 `/health` 未定义

- [ ] **Step 3: 写最小后端骨架实现**

```python
from fastapi import FastAPI

app = FastAPI(title="EduAgent API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

同时补齐 `pyproject.toml` 中的 FastAPI、uvicorn、sqlalchemy、httpx、pytest 等依赖，以及基础包结构。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/pyproject.toml backend/app backend/.env.example backend/tests/test_health.py
git commit -m "feat(backend): 初始化 FastAPI 工程骨架"
```

---

### Task 2: 建立数据库层与基础模型

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/chat.py`
- Create: `backend/app/models/profile.py`
- Create: `backend/app/models/resource.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_db_init.py`

- [ ] **Step 1: 写数据库初始化测试**

```python
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.chat import ChatSession


def test_create_tables_and_insert_session() -> None:
    with SessionLocal() as session:
        item = ChatSession(title="首次学习会话")
        session.add(item)
        session.commit()
        rows = session.execute(select(ChatSession)).scalars().all()
        assert len(rows) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_db_init.py -v`
Expected: FAIL，提示 `SessionLocal` 或模型不存在

- [ ] **Step 3: 写最小数据库实现**

实现内容：
- SQLite 数据库路径配置
- `Base`、`engine`、`SessionLocal`
- `init_db()` 启动建表
- `ChatSession`、`ChatMessage`、`StudentProfile`、`GeneratedResource` 四个模型

模型关键字段：
- `ChatSession`: `id`, `title`, `created_at`, `updated_at`
- `ChatMessage`: `id`, `session_id`, `role`, `content`, `message_type`, `created_at`
- `StudentProfile`: `id`, `user_id`(默认1), `session_id`(最后更新来源), `major`, `grade`, `knowledge_base`, `cognitive_style`, `learning_goal`, `weak_points`, `learning_pace`, `interest_areas`, `coding_level`, `weekly_hours`, `updated_at`
- `GeneratedResource`: `id`, `session_id`, `resource_type`, `title`, `content`, `knowledge_point`, `agent_name`, `created_at`

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_db_init.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/core/database.py backend/app/models backend/tests/conftest.py backend/tests/test_db_init.py
git commit -m "feat(backend): 添加 MVP 数据模型与数据库初始化"
```

---

### Task 3: 实现画像服务与响应模型

**Files:**
- Create: `backend/app/schemas/profile.py`
- Create: `backend/app/services/profile_service.py`
- Modify: `backend/app/models/profile.py`
- Create: `backend/tests/test_services/test_profile_service.py`

- [ ] **Step 1: 写画像创建与合并测试**

```python
def test_merge_profile_updates_only_provided_fields(profile_service) -> None:
    existing = {
        "major": "计算机专业",
        "learning_goal": "复习",
        "cognitive_style": "图文结合",
    }
    update = {
        "learning_goal": "考试复习",
        "weekly_hours": 8,
    }

    result = profile_service.merge_profile(existing, update)

    assert result["major"] == "计算机专业"
    assert result["learning_goal"] == "考试复习"
    assert result["weekly_hours"] == 8
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_profile_service.py -v`
Expected: FAIL，提示服务不存在

- [ ] **Step 3: 写最小实现**

实现内容：
- `ProfileResponse` Pydantic 模型
- `get_or_create_profile(user_id)`（MVP 阶段 user_id 固定为 1）
- `merge_profile(existing, update)`
- JSON 字段默认值标准化（空字典、空数组）
- `save_profile_update(user_id, update, session_id)`

要求：
- 画像绑定 user_id（默认用户 1），跨 session 累积更新
- 只覆盖传入字段
- 未提供字段不重置
- session_id 仅记录最后更新来源
- 返回结构稳定，前端可直接渲染

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_profile_service.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/schemas/profile.py backend/app/services/profile_service.py backend/tests/test_services/test_profile_service.py
git commit -m "feat(backend): 添加学生画像服务与响应模型"
```

---

### Task 4: 实现聊天服务与资源持久化

**Files:**
- Create: `backend/app/services/chat_service.py`
- Modify: `backend/app/models/chat.py`
- Modify: `backend/app/models/resource.py`
- Create: `backend/tests/test_services/test_chat_service.py`

- [ ] **Step 1: 写聊天服务测试**

```python
def test_create_session_and_persist_messages(chat_service) -> None:
    session_id = chat_service.create_session("首次学习会话")
    chat_service.save_message(session_id, "user", "帮我复习反向传播")
    chat_service.save_message(session_id, "assistant", "好的，下面开始")

    messages = chat_service.list_messages(session_id)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_services/test_chat_service.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- 创建会话
- 提供 `create_session()`，供独立创建会话接口与聊天补建会话共用
- 保存消息
- 查询会话消息
- 保存生成资源

要求：
- 若聊天请求未携带 `session_id`，能先创建真实会话再继续
- 不引入认证相关参数
- 保持单用户模式

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_services/test_chat_service.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/services/chat_service.py backend/tests/test_services/test_chat_service.py
git commit -m "feat(backend): 添加聊天会话与资源持久化服务"
```

---

### Task 5: 实现 RouterAgent

**Files:**
- Create: `backend/app/agents/router_agent.py`
- Create: `backend/tests/test_agents/test_router_agent.py`

- [ ] **Step 1: 写意图判定测试**

```python
from app.agents.router_agent import RouterAgent


def test_router_marks_profile_and_doc_for_learning_request() -> None:
    agent = RouterAgent()
    decision = agent.route("我是计算机专业大三学生，想复习反向传播")

    assert decision.update_profile is True
    assert decision.generate_document is True
    assert decision.topic == "反向传播"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_agents/test_router_agent.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- `RouteDecision` 数据结构
- 调用讯飞星火 Lite 做意图识别，prompt 要求输出结构化 JSON
- 从 LLM 响应中解析意图（update_profile / generate_document / chat）和主题关键词
- 降级逻辑：LLM 调用失败时回退到关键词匹配规则

LLM prompt 设计：
```
你是一个学习请求路由器。分析用户消息，输出 JSON：
{“update_profile”: bool, “generate_document”: bool, “topic”: “主题关键词”}
规则：
- 包含个人信息（专业/年级/基础/目标）→ update_profile=true
- 包含学习需求（复习/讲解/笔记/学习）→ generate_document=true
- 提取用户想学的核心主题作为 topic
```

降级规则（LLM 失败时）：
- 包含”我是/专业/大几/基础/目标”等信息 → `update_profile=True`
- 包含”复习/讲解/整理/笔记/学习资料”等信息 → `generate_document=True`
- 兜底：普通学习提问也生成文档

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_agents/test_router_agent.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/agents/router_agent.py backend/tests/test_agents/test_router_agent.py
git commit -m "feat(backend): 添加学习请求路由判定 Agent"
```

---

### Task 6: 实现 ProfileAgent

**Files:**
- Create: `backend/app/agents/profile_agent.py`
- Modify: `backend/app/services/profile_service.py`
- Create: `backend/tests/test_agents/test_profile_agent.py`

- [ ] **Step 1: 写画像抽取测试**

```python
from app.agents.profile_agent import ProfileAgent


def test_profile_agent_extracts_major_grade_goal_and_style() -> None:
    agent = ProfileAgent()
    update = agent.extract_profile_update(
        "我是计算机专业大三学生，机器学习基础一般，想复习反向传播，最好图文结合"
    )

    assert update["major"] == "计算机专业"
    assert update["grade"] == "大三"
    assert update["learning_goal"] == "复习"
    assert update["cognitive_style"] == "图文结合"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_agents/test_profile_agent.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- 调用讯飞星火 Lite 做画像字段抽取，prompt 要求输出结构化 JSON
- 基础字段：专业、年级、学习目标、认知风格、知识基础、学习节奏、编程水平、每周时间
- LLM 调用失败时降级为正则/关键词抽取
- 对未识别字段返回空更新

LLM prompt 设计：
```
从用户消息中提取学生画像信息，输出 JSON（只输出能确定的字段）：
{"major": "专业", "grade": "年级", "learning_goal": "目标",
 "cognitive_style": "认知风格", "coding_level": "编程水平", ...}
```

要求：
- 输出字段名与 `StudentProfile`、`ProfileResponse` 对齐
- 所有推断结果保持中文
- 抽取失败时不抛异常，由上层决定保留旧画像
- 画像更新调用 ProfileService 合并到默认用户的已有画像（跨 session 累积）

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_agents/test_profile_agent.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/agents/profile_agent.py backend/tests/test_agents/test_profile_agent.py backend/app/services/profile_service.py
git commit -m "feat(backend): 添加对话式学习画像提取 Agent"
```

---

### Task 7: 实现真实讯飞星火客户端与 DocAgent

**Files:**
- Create: `backend/app/core/llm.py`
- Create: `backend/app/agents/doc_agent.py`
- Create: `backend/tests/test_agents/test_doc_agent.py`

- [ ] **Step 1: 写 DocAgent 单元测试与星火客户端替身**

```python
from app.agents.doc_agent import DocAgent
from app.core.llm import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate_text(self, prompt: str) -> str:
        return "这是面向图文结合复习需求的反向传播讲义正文。"


a_sync_profile = {
    "major": "计算机专业",
    "grade": "大三",
    "cognitive_style": "图文结合",
    "learning_goal": "复习",
}


async def test_doc_agent_generates_personalized_document() -> None:
    agent = DocAgent(llm_client=StubLLMClient())

    document = await agent.generate_document("反向传播", a_sync_profile)

    assert document.title == "反向传播个性化学习讲义"
    assert "图文结合" in document.content or "反向传播" in document.content
    assert document.resource_type == "document"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_agents/test_doc_agent.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- `BaseLLMClient` 抽象接口
- `SparkLLMClient`：
  - 从环境变量读取 `SPARK_APP_ID`、`SPARK_API_KEY`、`SPARK_API_SECRET`
  - 封装真实讯飞星火 HTTP / WebSocket 请求
  - 将鉴权错误、网络错误、响应异常统一转换成中文业务异常
- `DocAgent` 根据 `topic + profile` 组装 prompt
- 输出结构包含 `title`, `resource_type`, `content`, `knowledge_point`, `agent_name`

要求：
- 默认必须走真实讯飞星火
- 不实现“伪成功”的 Mock 默认分支
- 测试里可以注入 stub client，但生产代码默认实例必须是 `SparkLLMClient`

- [ ] **Step 4: 增加凭证缺失错误测试**

```python
async def test_spark_client_raises_chinese_error_when_credentials_missing() -> None:
    ...
```

Run: `cd backend && uv run pytest tests/test_agents/test_doc_agent.py -v`
Expected: PASS，能覆盖正常生成与缺凭证错误路径

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/core/llm.py backend/app/agents/doc_agent.py backend/tests/test_agents/test_doc_agent.py
 git commit -m "feat(backend): 接入真实讯飞星火并完成文档生成 Agent"
```

---

### Task 8: 实现 orchestrator 事件流

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/agents/router_agent.py`
- Modify: `backend/app/agents/profile_agent.py`
- Modify: `backend/app/agents/doc_agent.py`
- Create: `backend/tests/test_agents/test_orchestrator.py`

- [ ] **Step 1: 写事件流顺序测试**

```python
async def test_orchestrator_yields_expected_event_sequence(orchestrator) -> None:
    events = [
        event
        async for event in orchestrator.run(
            session_id=1,
            user_message="我是计算机专业大三学生，想复习反向传播，最好图文结合",
        )
    ]

    event_types = [event.type for event in events]
    assert event_types[:3] == ["agent_status", "profile_updated", "agent_status"]
    assert event_types[3:-2]
    assert all(event_type == "token" for event_type in event_types[3:-2])
    assert event_types[-2:] == ["resource_card", "done"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_agents/test_orchestrator.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- `ChatRequest`、`SSEEvent`、`ResourceCardPayload` 等 schema
- orchestrator 串联：
  1. Router 判定
  2. 如需更新画像，发 `agent_status(Profile)`、保存画像、发 `profile_updated`
  3. 发 `agent_status(Doc)`
  4. 将正文切分为多个 `token`
  5. 保存资源并发 `resource_card`
  6. 发 `done`
- 异常时发 `error`

要求：
- 事件结构严格遵守 spec
- 成功顺序必须是：`agent_status(Profile)` → `profile_updated` → `agent_status(Doc)` → 多个 `token` → `resource_card` → `done`
- 若画像抽取失败：保留旧画像，但继续文档链路
- 若文档生成失败：返回 `error`，且不再发送后续成功事件

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_agents/test_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/schemas/chat.py backend/app/agents/orchestrator.py backend/tests/test_agents/test_orchestrator.py
 git commit -m "feat(backend): 添加聊天事件流编排器"
```

---

### Task 9: 实现聊天 SSE API

**Files:**
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/chat_service.py`
- Create: `backend/tests/test_api/test_chat_api.py`

- [ ] **Step 1: 写聊天接口测试**

```python
def test_chat_stream_returns_ordered_sse_events(client) -> None:
    response = client.post(
        "/api/chat/stream",
        json={"session_id": 1, "message": "帮我复习反向传播"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.index('"type":"agent_status"') < response.text.index('"type":"profile_updated"')
    assert response.text.index('"type":"profile_updated"') < response.text.index('"type":"resource_card"')
    assert response.text.index('"type":"resource_card"') < response.text.index('"type":"done"')
    assert response.text.count('"type":"token"') >= 1


def test_chat_stream_creates_session_when_session_id_missing(client) -> None:
    response = client.post(
        "/api/chat/stream",
        json={"message": "帮我复习反向传播"},
    )

    assert response.status_code == 200
    assert '"session_id":' in response.text


def test_chat_stream_stops_after_error_event(client) -> None:
    response = client.post(
        "/api/chat/stream",
        json={"session_id": 1, "message": "帮我复习反向传播"},
    )

    assert '"type":"error"' in response.text or '"type": "error"' in response.text
    error_marker = '"type":"error"' if '"type":"error"' in response.text else '"type": "error"'
    error_index = response.text.rindex(error_marker)
    assert '"type":"resource_card"' not in response.text[error_index:]
    assert '"type":"done"' not in response.text[error_index:]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_api/test_chat_api.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- `POST /api/chat/session`：创建空会话并返回真实 `session_id`
- `POST /api/chat/stream`
- 请求体：`session_id`, `message`
- 若未传 `session_id`，先创建真实会话并继续执行，并在响应事件中带回该 `session_id`
- 将用户消息落库
- 使用 `StreamingResponse` 返回 `text/event-stream`
- 将 orchestrator 事件序列编码成 SSE 文本块

SSE 格式示例：

```text
data: {"type":"agent_status","agent":"ProfileAgent","status":"working","message":"正在更新学习画像"}

```

- [ ] **Step 4: 增加错误路径测试**

验证：
- 星火凭证缺失时返回 `error` 事件，而不是裸 500
- SQLite 写入失败时返回统一中文错误
- `error` 事件发出后不再继续发送 `resource_card`、`done` 等成功事件
- 成功路径中事件顺序覆盖 `agent_status(Profile)` → `profile_updated` → `agent_status(Doc)` → `token` → `resource_card` → `done`
- 未传 `session_id` 时响应事件中带回真实会话标识，便于前端跳转与画像页读取

Run: `cd backend && uv run pytest tests/test_api/test_chat_api.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/api/chat.py backend/app/main.py backend/tests/test_api/test_chat_api.py
 git commit -m "feat(backend): 添加聊天 SSE 流式接口"
```

---

### Task 10: 实现画像查询 API

**Files:**
- Create: `backend/app/api/profile.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api/test_profile_api.py`

- [ ] **Step 1: 写画像接口测试**

```python
def test_profile_endpoint_returns_current_profile(client, seeded_profile) -> None:
    response = client.get("/api/profile?session_id=1")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == 1
    assert data["major"] == "计算机专业"
    assert "knowledge_base" in data


def test_profile_endpoint_creates_session_when_session_id_missing(client) -> None:
    response = client.get("/api/profile")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] > 0
    assert "major" in data
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_api/test_profile_api.py -v`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- `GET /api/profile?session_id=1`
- 调用 `ProfileService.get_or_create_profile`
- 若未传 `session_id`，先创建真实会话，再返回该会话对应的默认画像与新 `session_id`
- 返回稳定 JSON 结构

要求：
- 即使首次访问没有画像，也返回完整默认结构
- 响应中显式带回 `session_id`，便于前端保持聊天页与画像页链路一致
- 响应字段命名与前端展示一致

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_api/test_profile_api.py -v`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add backend/app/api/profile.py backend/app/main.py backend/tests/test_api/test_profile_api.py
git commit -m "feat(backend): 添加学习画像查询接口"
```

---

### Task 11: 初始化前端工程与暖色主题布局

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/eslint.config.mjs`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/(main)/layout.tsx`
- Create: `frontend/.env.example`
- Create: `frontend/tests/layout.test.tsx`

- [ ] **Step 1: 写布局渲染测试**

```tsx
import { render, screen } from "@testing-library/react";
import RootLayout from "@/app/layout";


test("root layout renders Chinese shell", () => {
  render(
    <RootLayout>
      <div>内容</div>
    </RootLayout>
  );

  expect(screen.getByText("EduAgent")).toBeInTheDocument();
  expect(screen.getByText("内容")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && pnpm test layout.test.tsx`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- Next.js 基础配置
- Vitest + Testing Library + jsdom 测试配置
- 全局 Tailwind 与暖色主题变量
- 根布局与主布局导航
- 首页加载时先调用后端创建会话接口，成功后跳转到真实 `/chat/<session_id>` 路径

要求：
- 遵循 `CLAUDE.md` 中的暖色设计约束
- UI 文案全部中文
- `package.json` 中显式提供 `pnpm test` 脚本，并确保测试命令实际走 Vitest

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && pnpm test layout.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add frontend/package.json frontend/app frontend/tailwind.config.ts frontend/tests/layout.test.tsx
 git commit -m "feat(frontend): 初始化 Next.js 工程与暖色主题布局"
```

---

### Task 12: 实现前端类型、API 与 SSE 客户端

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/sse.ts`
- Create: `frontend/tests/sse.test.ts`

- [ ] **Step 1: 写 SSE 解析测试**

```ts
import { parseSSEChunk } from "@/lib/sse";

test("parseSSEChunk returns JSON payload from data line", () => {
  const result = parseSSEChunk('data: {"type":"done"}\n\n');
  expect(result).toEqual([{ type: "done" }]);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && pnpm test sse.test.ts`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- 定义 `Profile`, `ChatEvent`, `ResourceCard`, `AgentStatusEvent` 类型
- `fetchProfile(sessionId)`
- `createSession()`
- `streamChat(sessionId, message, handlers)`
- `parseSSEChunk()`
- 增加客户端消费约束：收到 `error` 事件后立即停止后续成功事件处理，并展示中文错误提示

要求：
- 采用浏览器 `fetch` + `ReadableStream` 解析 `POST /api/chat/stream`
- 不使用原生 `EventSource`，因为聊天接口为 POST
- 保证错误处理与中文提示兼容
- 前端请求封装明确区分“创建会话”“读取画像”“发送聊天消息”三类调用

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && pnpm test sse.test.ts`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add frontend/lib frontend/tests/sse.test.ts
git commit -m "feat(frontend): 添加前端 API 与 SSE 客户端封装"
```

---

### Task 13: 实现聊天 UI 基础组件

**Files:**
- Create: `frontend/components/chat/ChatMessage.tsx`
- Create: `frontend/components/chat/StreamingText.tsx`
- Create: `frontend/components/chat/ResourceCard.tsx`
- Create: `frontend/components/chat/AgentStatus.tsx`
- Create: `frontend/tests/chat-components.test.tsx`

- [ ] **Step 1: 写组件渲染测试**

```tsx
test("resource card renders Chinese title and content", () => {
  render(
    <ResourceCard
      resource={{
        id: 1,
        resource_type: "document",
        title: "反向传播个性化学习讲义",
        content: "这里是内容",
      }}
    />
  );

  expect(screen.getByText("反向传播个性化学习讲义")).toBeInTheDocument();
  expect(screen.getByText("这里是内容")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && pnpm test chat-components.test.tsx`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- 用户消息 / 助手消息气泡
- 流式文本增量显示
- 资源卡片
- Agent 状态条

要求：
- 风格遵循暖色主题
- 状态、按钮、标题、提示全部为中文
- 不增加超出首切片的交互复杂度

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && pnpm test chat-components.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add frontend/components/chat frontend/tests/chat-components.test.tsx
git commit -m "feat(frontend): 添加聊天消息、状态与资源卡片组件"
```

---

### Task 14: 实现聊天页闭环

**Files:**
- Create: `frontend/app/(main)/chat/[sessionId]/page.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/sse.ts`
- Modify: `frontend/components/chat/*.tsx`
- Create: `frontend/tests/chat-page.test.tsx`

- [ ] **Step 1: 写聊天页集成测试**

```tsx
test("chat page sends message and renders streaming result", async () => {
  render(<ChatPage params={{ sessionId: "1" }} />);

  await userEvent.type(screen.getByPlaceholderText("请输入你的学习需求"), "帮我复习反向传播");
  await userEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("正在更新学习画像")).toBeInTheDocument();
  expect(await screen.findByText(/反向传播/)).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && pnpm test chat-page.test.tsx`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- 消息列表状态
- 输入框与发送按钮
- 调用 `streamChat()`
- 处理 `agent_status`、`profile_updated`、`token`、`resource_card`、`error`、`done`
- 当响应中返回新的 `session_id` 时，同步更新当前路由与“查看画像”跳转链接
- 显示中文错误态与空态

要求：
- 真实会话 ID 直接使用 URL 参数，并允许在首条消息后被后端回传的新 `session_id` 覆盖
- 页面初次可显示欢迎文案
- 聊天失败时展示“连接已中断，请重试”或具体中文错误
- 提供跳转到 `/profile?session_id=<session_id>` 的明确入口
- 不接入复杂历史会话切换

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && pnpm test chat-page.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add frontend/app/(main)/chat/[sessionId]/page.tsx frontend/lib frontend/tests/chat-page.test.tsx
git commit -m "feat(frontend): 完成聊天页流式对话闭环"
```

---

### Task 15: 实现画像页展示

**Files:**
- Create: `frontend/components/profile/ProfileSummary.tsx`
- Create: `frontend/app/(main)/profile/page.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/tests/profile-page.test.tsx`

- [ ] **Step 1: 写画像页测试**

```tsx
test("profile page renders six-plus dimensions in Chinese", async () => {
  render(<ProfilePage searchParams={{ session_id: "1" }} />);

  expect(await screen.findByText("学习画像")).toBeInTheDocument();
  expect(await screen.findByText("专业")).toBeInTheDocument();
  expect(await screen.findByText("认知风格")).toBeInTheDocument();
  expect(await screen.findByText("学习目标")).toBeInTheDocument();
  expect(await screen.findByText("学习节奏")).toBeInTheDocument();
});


test("profile page creates session when session_id is missing", async () => {
  render(<ProfilePage searchParams={{}} />);

  expect(await screen.findByText("学习画像")).toBeInTheDocument();
  expect(await screen.findByText("专业")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && pnpm test profile-page.test.tsx`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

实现内容：
- `ProfileSummary` 展示 6+ 维画像字段
- 画像页优先从 `searchParams.session_id` 读取当前会话标识并调用 `fetchProfile()`
- 若缺少 `session_id`，前端主动调用画像接口获取后端补建的真实会话与画像数据，再用返回的新 `session_id` 更新页面内跳转链接
- 加载中、失败、空数据的中文状态

要求：
- 暂不引入图表库
- 先用结构化卡片展示，保证内容清晰
- 页面跳转链路固定为 `/profile?session_id=<session_id>`，与聊天页保持同一个真实 `session_id`
- 不再使用“先从聊天页进入”的纯前端引导态替代后端补建会话逻辑

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && pnpm test profile-page.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交当前任务**

```bash
git add frontend/components/profile/ProfileSummary.tsx frontend/app/(main)/profile/page.tsx frontend/tests/profile-page.test.tsx
git commit -m "feat(frontend): 添加学习画像展示页面"
```

---

### Task 16: 联调、手工验证与收尾

**Files:**
- Modify: `backend/app/main.py`
- Modify: `frontend/package.json`
- Modify: `frontend/app/(main)/chat/[sessionId]/page.tsx`
- Modify: `frontend/app/(main)/profile/page.tsx`
- Test: `backend/tests/**/*`
- Test: `frontend/tests/**/*`

- [ ] **Step 1: 运行后端全部测试**

Run: `cd backend && uv run pytest`
Expected: 全部 PASS

- [ ] **Step 2: 运行前端全部测试**

Run: `cd frontend && pnpm test`
Expected: 全部 PASS

- [ ] **Step 3: 启动后端开发服务**

Run: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
Expected: 服务启动成功

- [ ] **Step 4: 启动前端开发服务**

Run: `cd frontend && pnpm dev`
Expected: 前端启动在 `localhost:3000`

- [ ] **Step 5: 手工验证聊天页黄金路径**

验证：
- 访问首页 `/`，确认前端先请求后端创建真实会话，再自动跳转到 `/chat/<session_id>`
- 或直接访问已创建的 `/chat/1` 之类真实会话路径
- 输入“我是计算机专业大三学生，机器学习基础一般，想复习反向传播，最好有图文结合的讲解”
- 看到“正在更新学习画像 / 正在生成学习文档”
- 看到中文流式文本输出
- 看到 `document` 类型资源卡片

- [ ] **Step 6: 手工验证画像页**

验证：
- 从聊天页使用当前会话参数跳转到 `/profile?session_id=<session_id>`
- 看到专业、年级、学习目标、认知风格、知识基础、学习节奏等字段已更新
- 确认画像页展示的是刚刚聊天写入的同一会话画像

- [ ] **Step 7: 手工验证真实讯飞错误路径**

验证：
- 去掉星火凭证后重新请求
- 前端展示明确中文失败提示
- 后端返回 `error` 事件而不是伪造内容

- [ ] **Step 8: 修复联调发现的问题并重复测试**

Run:
- `cd backend && uv run pytest`
- `cd frontend && pnpm test`

Expected: PASS

- [ ] **Step 9: 最终提交当前批次**

```bash
git add backend frontend
git commit -m "feat: 完成 EduAgent 对话 MVP 首个可交付切片"
```

---

## 实施注意事项

- 所有前端 UI 文案必须为中文，遵守 `CLAUDE.md`
- 不要在首切片引入登录、RAG、路径规划、Quiz/Code/Media 等超范围能力
- 后端保持 API 层薄、service 层厚，Agent 只做识别/抽取/生成，不做持久化
- `SparkLLMClient` 必须是真实可调用实现，不允许以 Mock 或占位返回伪成功内容
- 若星火凭证缺失或调用失败，必须返回明确中文错误事件
- 画像页先以清晰的信息卡片呈现，不要过早引入雷达图
- 聊天接口为 POST + SSE，前端应使用 `fetch` 流式消费而不是 `EventSource`
- 若项目仍未初始化 git，则跳过 commit 步骤，但保留计划中的提交节点，待仓库初始化后执行
- **画像绑定默认用户（user_id=1）**，跨 session 累积更新，不随新会话重置
- **Router/Profile Agent 使用讯飞星火 Lite**（非纯正则），星火调用失败时降级为关键词匹配

## 测试 Mock 策略

### 后端测试

- **LLM 客户端**: 所有 Agent 测试通过注入 `StubLLMClient` 替代真实星火调用，stub 返回预定义的结构化 JSON
- **Router/Profile Agent 测试**: 注入 stub 返回预设意图判定/画像提取结果，验证下游逻辑正确性
- **集成测试中的 LLM**: conftest.py 中提供 `mock_llm_client` fixture，自动替换全局 LLM 实例
- **真实星火测试**: 仅在 CI 中标记为 `@pytest.mark.integration`，需要环境变量 `SPARK_APP_ID` 等存在才执行

### 前端测试

- **API Mock**: 使用 MSW (Mock Service Worker) 拦截 fetch 请求，模拟后端 SSE 响应
- **SSE Mock**: MSW handler 返回 `text/event-stream` 格式的预定义事件序列
- **组件测试**: 直接传 props，不涉及网络调用
- **安装**: `pnpm add -D msw`，在 `frontend/tests/mocks/` 中定义 handlers

### 开发模式（SPARK_DEV_MODE）

为解决开发阶段星火凭证不可用的问题，增加开发模式环境变量：

```bash
# backend/.env
SPARK_DEV_MODE=true  # 仅开发调试使用，演示/提交时必须设为 false
```

当 `SPARK_DEV_MODE=true` 时：
- LLM 客户端使用 `DevLLMClient`，返回合理的中文模拟内容（非空字符串，结构完整）
- 响应中附带 `[开发模式]` 前缀标记，确保不会与真实生成内容混淆
- Router/Profile Agent 降级为关键词匹配逻辑
- 日志中打印明确警告："⚠️ 当前为开发模式，LLM 响应为模拟内容"

当 `SPARK_DEV_MODE=false`（默认）或未设置时：
- 必须配置真实星火凭证，缺失时返回中文错误事件
- 不允许伪造内容

## 测试命令汇总

### 后端

```bash
cd backend
uv run pytest
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
pnpm install
pnpm test
pnpm dev
```

### 手工验证重点

1. 聊天页是否能发送消息
2. SSE 是否真实流式更新而非一次性返回
3. Agent 状态是否按顺序显示
4. 文档卡片是否渲染
5. 画像页是否读取到聊天更新后的数据
6. 星火失败时是否返回中文错误而不是伪造结果
7. 所有错误提示是否为中文
