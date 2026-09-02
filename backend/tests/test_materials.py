"""会话学习材料兜底生成 — 行为测试。

覆盖四条关键路径：
1. 材料按会话隔离：知识库检索不返回材料，材料检索不返回知识库。
2. 知识库置信度足够 → 使用知识库（kind=knowledge）。
3. 知识库不足 → 兜底到会话材料（kind=material），并带材料文件名。
4. 删除材料后，材料检索不再命中。
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents.common import build_anchored_context
from app.wiki.embeddings import DevEmbedding
from app.wiki.graph import KnowledgeGraph
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore
from app.wiki.wiki_service import WikiService

KB_TOPIC = "梯度下降 是参数优化方法，通过不断迭代更新参数。"
MATERIAL_TOPIC = "TCP 三次握手 是建立可靠连接的过程：SYN、SYN-ACK、ACK。"
QUERY = "TCP 三次握手"


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
    return WikiService(
        rag_engine=rag,
        knowledge_graph=graph,
        vector_store=vector_store,
    )


async def _ingest_material(wiki: WikiService, *, session_id: int = 7) -> None:
    await wiki.ingest_uploaded_document(
        filename="student-notes.md",
        content=MATERIAL_TOPIC.encode("utf-8"),
        mime_type="text/markdown",
        session_id=session_id,
    )


def test_session_material_is_isolated_from_kb_search() -> None:
    asyncio.run(_test_isolated())


async def _test_isolated() -> None:
    wiki = _build_wiki()
    await _ingest_material(wiki)

    # 知识库检索（course_id=None，全知识库）不得返回会话材料
    kb_results = await wiki.search(QUERY, course_id=None)
    assert all(result.course_id != "session:7" for result in kb_results)

    # 知识库按课程检索也不返回材料
    course_results = await wiki.search(QUERY, course_id="cn-net")
    assert all(result.course_id != "session:7" for result in course_results)

    # 会话材料检索只返回该会话的材料
    material_results = await wiki.search(QUERY, session_id=7)
    assert material_results, "会话材料应可被检索到"
    assert all(result.course_id == "session:7" for result in material_results)
    assert all(result.chapter == "material" for result in material_results)


def test_build_anchored_context_falls_back_to_material() -> None:
    asyncio.run(_test_fallback())


async def _test_fallback() -> None:
    wiki = _build_wiki()
    await _ingest_material(wiki)

    anchored = await build_anchored_context(
        wiki,
        query=QUERY,
        course_id="cn-net",
        session_id=7,
    )
    assert anchored.kind == "material", f"期望材料兜底，实际: {anchored.kind}"
    assert anchored.context
    assert anchored.material_titles, "材料来源文件名应被记录"


def test_build_anchored_context_uses_knowledge_when_confident() -> None:
    asyncio.run(_test_knowledge())


async def _test_knowledge() -> None:
    wiki = _build_wiki()
    await _ingest_material(wiki)

    anchored = await build_anchored_context(
        wiki,
        query="梯度下降 参数优化",
        course_id="cn-net",
        session_id=7,
    )
    assert anchored.kind == "knowledge", f"期望知识库，实际: {anchored.kind}"
    assert anchored.context


def test_build_anchored_context_none_when_no_coverage() -> None:
    asyncio.run(_test_none())


async def _test_none() -> None:
    wiki = _build_wiki()

    anchored = await build_anchored_context(
        wiki,
        query="量子计算 叠加态 纠缠",
        course_id="cn-net",
        session_id=7,
    )
    assert anchored.kind == "none"
    assert anchored.context == ""


def test_delete_material_removes_chunks() -> None:
    asyncio.run(_test_delete())


async def _test_delete() -> None:
    wiki = _build_wiki()
    result = await wiki.ingest_uploaded_document(
        filename="temp-notes.md",
        content=MATERIAL_TOPIC.encode("utf-8"),
        mime_type="text/markdown",
        session_id=9,
    )
    assert await wiki.search(QUERY, session_id=9)

    await wiki.delete_chunks(result.chunk_ids)
    assert not await wiki.search(QUERY, session_id=9)


def test_attach_material_gives_actionable_error() -> None:
    """材料解析失败时给出可读指引（空内容/格式不支持），而非裸异常。"""
    asyncio.run(_test_actionable_error())


async def _test_actionable_error() -> None:
    from app.services.material_service import SessionMaterialError
    from app.wiki.ingestion import (
        UnsupportedDocumentTypeError,
        extract_upload_text,
    )

    # 空内容 → 可读错误（语义化文案）而非裸抛
    with pytest.raises(SessionMaterialError) as err:
        _raise_if_empty("notes.md", extract_upload_text(filename="notes.md", content=b"   "))
    assert "未解析出可入库文本" in str(err.value)

    # 不支持的格式 → 可读错误（含格式清单指引）
    with pytest.raises(UnsupportedDocumentTypeError) as err:
        extract_upload_text(filename="notes.docx", content=b"hello")
    assert "格式不支持" in str(err.value) or "仅支持" in str(err.value)


def _raise_if_empty(filename: str, text: str) -> None:
    from app.services.material_service import SessionMaterialError

    if not text.strip():
        raise SessionMaterialError(f"材料 {filename} 未解析出可入库文本")


# —— 审计修复回归：MCP 归属校验 + 三态语义 ——


class _RecordingLLM:
    """记录 prompt 的最小 LLM 桩。"""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "这是一份个性化学习讲义。"


class _StubAssetStorage:
    """不落盘的最小资产存储桩。"""

    class _Stored:
        def __init__(self, key: str) -> None:
            self.key = key

    def save_bytes(self, *, data, filename, media_type, namespace):
        return _StubAssetStorage._Stored(key=f"{namespace}/{filename}")

    def resolve(self, key):
        return None


def test_attach_material_validates_session_access() -> None:
    """MCP 形态（user_id=None）也必须校验会话存在，杜绝孤儿材料行。"""
    asyncio.run(_test_attach_access())


async def _test_attach_access() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.models.chat import ChatSession
    from app.services.material_service import (
        SessionMaterialError,
        SessionMaterialService,
    )

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    wiki = _build_wiki()
    try:
        async with factory() as db:
            chat = ChatSession(title="MCP 形态会话")
            db.add(chat)
            await db.commit()
            session_id = chat.id
            service = SessionMaterialService(
                session=db, wiki_service=wiki, asset_storage=_StubAssetStorage()
            )

            # 会话不存在 → 拒绝（user_id=None 也不放行，防孤儿行）
            with pytest.raises(SessionMaterialError, match="会话不存在"):
                await service.attach_material(
                    session_id=session_id + 1000,
                    user_id=None,
                    filename="notes.md",
                    content=MATERIAL_TOPIC.encode("utf-8"),
                )

            # 会话存在 + user_id=None（MCP 可信宿主）→ 放行并完成摄取
            material = await service.attach_material(
                session_id=session_id,
                user_id=None,
                filename="notes.md",
                content=MATERIAL_TOPIC.encode("utf-8"),
                mime_type="text/markdown",
            )
            assert material.chunk_count >= 1

            # 会话存在但归属他人 → 拒绝（Web 形态归属校验保持不变）
            with pytest.raises(SessionMaterialError, match="会话不存在"):
                await service.attach_material(
                    session_id=session_id,
                    user_id=424242,
                    filename="notes.md",
                    content=MATERIAL_TOPIC.encode("utf-8"),
                )
    finally:
        await engine.dispose()


def test_mcp_search_material_requires_existing_session() -> None:
    """MCP search_material 先校验会话存在，堵住任意 session_id 检索他人材料。"""
    asyncio.run(_test_mcp_search_access())


async def _test_mcp_search_access() -> None:
    from types import SimpleNamespace

    import app.core.database as database_module
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.mcp_server import EduAgentTools
    from app.models.chat import ChatSession

    class _StubWiki:
        async def search(self, query, top_k=5, session_id=None):
            return [
                SimpleNamespace(
                    title="学生笔记",
                    content="材料片段",
                    score=0.9,
                    course_id=f"session:{session_id}",
                )
            ]

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    original_factory = database_module.AsyncSessionLocal
    database_module.AsyncSessionLocal = factory
    try:
        async with factory() as db:
            chat = ChatSession(title="MCP 校验会话")
            db.add(chat)
            await db.commit()
            session_id = chat.id

        tools = EduAgentTools(
            router=None,
            profile=None,
            doc=None,
            quiz=None,
            code=None,
            media=None,
            reading=None,
            tutor=None,
            wiki=_StubWiki(),
        )
        with pytest.raises(ValueError, match="不存在"):
            await tools.search_material(
                session_id=session_id + 1000, query="TCP 三次握手"
            )
        rows = await tools.search_material(session_id=session_id, query="TCP 三次握手")
        assert rows and rows[0]["course_id"] == f"session:{session_id}"
    finally:
        database_module.AsyncSessionLocal = original_factory
        await engine.dispose()


def test_doc_agent_material_anchor_is_trusted_context() -> None:
    """材料锚定是有来源的可信生成：三态标记 material，不触发兜底告警。"""
    asyncio.run(_test_doc_material_anchor())


async def _test_doc_material_anchor() -> None:
    from app.agents.doc_agent import DocAgent

    wiki = _build_wiki()
    await _ingest_material(wiki)
    agent = DocAgent(llm_client=_RecordingLLM(), wiki_service=wiki)

    anchored = await agent.generate_document(
        QUERY, None, course_id="cn-net", session_id=7
    )
    assert anchored.context_kind == "material"
    assert anchored.wiki_fallback is False

    uncovered = await agent.generate_document(
        "量子计算 叠加态 纠缠", None, course_id="cn-net", session_id=7
    )
    assert uncovered.context_kind == "none"
    assert uncovered.wiki_fallback is True
