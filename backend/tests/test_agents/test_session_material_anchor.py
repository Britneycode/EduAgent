"""生成类 Agent 的会话材料锚定 — 行为测试。

对齐 build_anchored_context 的三态语义（知识库 → 会话材料 → 无覆盖）：
1. 不传 session_id：行为与既有版本完全一致，会话材料不参与生成。
2. 传 session_id 且知识库未命中：prompt 上下文包含材料内容，context_kind=material。
3. 传 session_id 且知识库命中：仍用知识库（kind=knowledge），不混入材料。
4. CodeAgent 代码校验状态写入 metadata["code_validation"]。

ORM 造会话 + SessionMaterialService 挂材料的手法抄自 tests/test_materials.py。
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.code_agent import CodeAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.reading_agent import ReadingAgent
from app.core.code_sandbox import extract_python_code, validate_python_code
from app.core.database import Base
from app.core.llm import BaseLLMClient
from app.models.chat import ChatSession
from app.services.material_service import SessionMaterialService
from app.wiki.embeddings import DevEmbedding
from app.wiki.graph import KnowledgeGraph
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore
from app.wiki.wiki_service import WikiService

KB_TOPIC = "梯度下降 是参数优化方法，通过不断迭代更新参数。"
MATERIAL_TOPIC = "TCP 三次握手 是建立可靠连接的过程：SYN、SYN-ACK、ACK。"
MATERIAL_MARK = "SYN-ACK"  # 材料独有内容，用于断言是否进入 prompt
QUERY = "TCP 三次握手"  # 知识库不覆盖、仅材料覆盖的查询
KB_QUERY = "梯度下降 参数优化"  # 知识库命中的查询

PROFILE = {"learning_goal": "复习", "cognitive_style": "图文结合"}

# 非 JSON 回复：让 QuizAgent 结构化路径失败，回退 Markdown 路径（两条 prompt 都可断言）
PLAIN_REPLY = "1. 基础理解题\n答案：用于检验概念理解。"
SAFE_CODE_REPLY = """## 代码目标
结合学生材料演示三次握手。

```python
print("TCP 三次握手")
print(1 + 2)
```

## 预期输出
会输出主题和数字 3。
"""
NO_CODE_REPLY = "一、代码目标\n只有文字说明，没有代码块。"


class PromptRecordingLLM(BaseLLMClient):
    """记录 prompt 的最小 LLM 桩，按脚本依次返回内容。"""

    def __init__(self, replies: list[str]) -> None:
        self.prompts: list[str] = []
        self._replies = replies

    async def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        index = min(len(self.prompts) - 1, len(self._replies) - 1)
        return self._replies[index]


def _build_wiki() -> WikiService:
    vector_store = VectorStore(embedding_client=DevEmbedding())
    vector_store.add(
        chunk_ids=["kb_1"],
        documents=[KB_TOPIC],
        metadatas=[
            {
                "title": "梯度下降",
                "chapter": "ch4",
                "section": "s1",
                "course_id": "cn-net",
                "scope": "knowledge",
            }
        ],
    )
    rag = RAGEngine(vector_store=vector_store)
    graph = KnowledgeGraph()
    return WikiService(rag_engine=rag, knowledge_graph=graph, vector_store=vector_store)


class _StubAssetStorage:
    """不落盘的最小资产存储桩（抄自 tests/test_materials.py）。"""

    class _Stored:
        def __init__(self, key: str) -> None:
            self.key = key

    def save_bytes(self, *, data, filename, media_type, namespace):
        return _StubAssetStorage._Stored(key=f"{namespace}/{filename}")

    def resolve(self, key):
        return None


async def _make_session_with_material(wiki: WikiService) -> int:
    """ORM 建 ChatSession 并经 SessionMaterialService 挂一份学习材料。"""
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            chat = ChatSession(title="材料锚定测试会话")
            db.add(chat)
            await db.commit()
            session_id = chat.id
            service = SessionMaterialService(
                session=db, wiki_service=wiki, asset_storage=_StubAssetStorage()
            )
            await service.attach_material(
                session_id=session_id,
                user_id=None,
                filename="student-notes.md",
                content=MATERIAL_TOPIC.encode("utf-8"),
                mime_type="text/markdown",
            )
        return session_id
    finally:
        await engine.dispose()


# —— 不传 session_id：行为与既有版本完全一致 ——


def test_quiz_agent_without_session_id_keeps_current_behavior() -> None:
    asyncio.run(_run_quiz_without_session())


async def _run_quiz_without_session() -> None:
    wiki = _build_wiki()
    await _make_session_with_material(wiki)  # 材料存在，但不传 session_id
    llm = PromptRecordingLLM([PLAIN_REPLY])
    agent = QuizAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_quiz(QUERY, PROFILE, course_id="cn-net")

    # 旧行为：KB 低相关结果照用（返回梯度下降 chunk）、材料不参与、无三态标记
    assert resource.context_kind == ""
    assert MATERIAL_MARK not in resource.wiki_context
    assert llm.prompts, "LLM 应被调用"
    assert all(MATERIAL_MARK not in prompt for prompt in llm.prompts)


def test_code_agent_without_session_id_keeps_current_behavior() -> None:
    asyncio.run(_run_code_without_session())


async def _run_code_without_session() -> None:
    wiki = _build_wiki()
    await _make_session_with_material(wiki)
    llm = PromptRecordingLLM([SAFE_CODE_REPLY])
    agent = CodeAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_code(QUERY, PROFILE, course_id="cn-net")

    # 旧行为：KB 低相关结果照用、材料不参与、无三态标记
    assert resource.context_kind == ""
    assert MATERIAL_MARK not in resource.wiki_context
    assert all(MATERIAL_MARK not in prompt for prompt in llm.prompts)


def test_reading_agent_without_session_id_keeps_current_behavior() -> None:
    asyncio.run(_run_reading_without_session())


async def _run_reading_without_session() -> None:
    wiki = _build_wiki()
    await _make_session_with_material(wiki)
    llm = PromptRecordingLLM([PLAIN_REPLY])
    agent = ReadingAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_reading(QUERY, PROFILE, course_id="cn-net")

    # 旧行为：KB 低相关结果照用、材料不参与、无三态标记
    assert resource.context_kind == ""
    assert MATERIAL_MARK not in resource.wiki_context
    assert all(MATERIAL_MARK not in prompt for prompt in llm.prompts)


# —— 传 session_id：知识库未命中时兜底到会话材料 ——


def test_quiz_agent_uses_session_material_when_kb_misses() -> None:
    asyncio.run(_run_quiz_material())


async def _run_quiz_material() -> None:
    wiki = _build_wiki()
    session_id = await _make_session_with_material(wiki)
    # 非 JSON 回复 → 结构化与 Markdown 两条 prompt 路径都执行
    llm = PromptRecordingLLM([PLAIN_REPLY])
    agent = QuizAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_quiz(
        QUERY, PROFILE, course_id="cn-net", session_id=session_id
    )

    assert resource.context_kind == "material"
    assert resource.wiki_fallback is False
    assert MATERIAL_MARK in resource.wiki_context
    assert len(llm.prompts) >= 1
    for prompt in llm.prompts:  # 两条 prompt 路径都要吃到材料锚定
        assert MATERIAL_MARK in prompt
        assert "学生上传的学习材料" in prompt
        assert "📎 student-notes.md" in prompt


def test_quiz_agent_prefers_knowledge_base_when_confident() -> None:
    asyncio.run(_run_quiz_knowledge())


async def _run_quiz_knowledge() -> None:
    wiki = _build_wiki()
    session_id = await _make_session_with_material(wiki)
    llm = PromptRecordingLLM([PLAIN_REPLY])
    agent = QuizAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_quiz(
        KB_QUERY, PROFILE, course_id="cn-net", session_id=session_id
    )

    assert resource.context_kind == "knowledge"
    assert resource.wiki_fallback is False
    assert "梯度下降" in resource.wiki_context
    assert all(MATERIAL_MARK not in prompt for prompt in llm.prompts)


def test_code_agent_uses_session_material_when_kb_misses() -> None:
    asyncio.run(_run_code_material())


async def _run_code_material() -> None:
    wiki = _build_wiki()
    session_id = await _make_session_with_material(wiki)
    llm = PromptRecordingLLM([SAFE_CODE_REPLY])
    agent = CodeAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_code(
        QUERY, PROFILE, course_id="cn-net", session_id=session_id
    )

    assert resource.context_kind == "material"
    assert resource.wiki_fallback is False
    assert MATERIAL_MARK in resource.wiki_context
    assert MATERIAL_MARK in llm.prompts[0]
    assert "学生上传的学习材料" in llm.prompts[0]
    assert "📎 student-notes.md" in llm.prompts[0]


def test_reading_agent_uses_session_material_when_kb_misses() -> None:
    asyncio.run(_run_reading_material())


async def _run_reading_material() -> None:
    wiki = _build_wiki()
    session_id = await _make_session_with_material(wiki)
    llm = PromptRecordingLLM([PLAIN_REPLY])
    agent = ReadingAgent(llm_client=llm, wiki_service=wiki)

    resource = await agent.generate_reading(
        QUERY, PROFILE, course_id="cn-net", session_id=session_id
    )

    assert resource.context_kind == "material"
    assert resource.wiki_fallback is False
    assert MATERIAL_MARK in resource.wiki_context
    assert MATERIAL_MARK in llm.prompts[0]
    assert "学生上传的学习材料" in llm.prompts[0]
    assert "📎 student-notes.md" in llm.prompts[0]


# —— CodeAgent 校验状态写入 metadata ——


def test_code_agent_reports_code_validation_status() -> None:
    asyncio.run(_run_code_validation())


async def _run_code_validation() -> None:
    wiki = _build_wiki()
    agent = CodeAgent(
        llm_client=PromptRecordingLLM([SAFE_CODE_REPLY]), wiki_service=wiki
    )
    passed = await agent.generate_code(QUERY, PROFILE, session_id=None)
    assert passed.metadata["code_validation"] == "passed"

    fallback_agent = CodeAgent(
        llm_client=PromptRecordingLLM([NO_CODE_REPLY]), wiki_service=wiki
    )
    fallback = await fallback_agent.generate_code(QUERY, PROFILE, session_id=None)
    assert fallback.metadata["code_validation"] == "fallback"
    # 兜底内容本身必须是可运行的安全代码
    code = extract_python_code(fallback.content)
    validate_python_code(code)
