"""MCP 会话工具链回归测试。

覆盖审计 P0「材料工具链死锁」修复与协议健壮性：
1. 默认会话 get_or_create 幂等（同标题复用最新一条，不重复创建）。
2. attach_material / search_material 省略 session_id 时自动落默认会话。
3. 显式传不存在的 session_id → 报错文案含自救指引。
4. create_session / list_sessions 工具（含最近 20 条限量）。
5. extract_profile persist=true 按单学生落库。
6. tutor_answer 的 history 字符串解析透传。
7. 畸形 JSON 行回标准 -32700 Parse error 帧后继续读下一行。
8. 合法 JSON 但非请求对象（数组/字符串行）回 -32600 帧，服务循环不断。
"""

from __future__ import annotations

import asyncio
import json
import sys

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.mcp_server import TOOLS, EduAgentTools, _parse_error_frame, _parse_history

MATERIAL_TEXT = "TCP 三次握手 是建立可靠连接的过程：SYN、SYN-ACK、ACK。"


def _build_offline_wiki():
    """构建离线可用的 WikiService（DevEmbedding，不依赖外部向量库）。"""
    from app.wiki.embeddings import DevEmbedding
    from app.wiki.graph import KnowledgeGraph
    from app.wiki.rag_engine import RAGEngine
    from app.wiki.vector_store import VectorStore
    from app.wiki.wiki_service import WikiService

    vector_store = VectorStore(embedding_client=DevEmbedding())
    rag = RAGEngine(vector_store=vector_store)
    return WikiService(
        rag_engine=rag,
        knowledge_graph=KnowledgeGraph(),
        vector_store=vector_store,
    )


class _StubAssetStorage:
    """不落盘的最小资产存储桩。"""

    class _Stored:
        def __init__(self, key: str) -> None:
            self.key = key

    def save_bytes(self, *, data, filename, media_type, namespace):
        return _StubAssetStorage._Stored(key=f"{namespace}/{filename}")

    def resolve(self, key):
        return None


class _StubTutor:
    """记录 answer 入参的最小答疑桩。"""

    def __init__(self) -> None:
        self.kwargs: dict | None = None

    async def answer(self, question, profile, **kwargs) -> str:
        self.kwargs = {"profile": profile, **kwargs}
        return "好的，我们继续。"


class _FakeStdin:
    """模拟 stdio 输入：逐行返回，读完后返回空串触发退出。"""

    def __init__(self, lines: list[str]) -> None:
        self._lines = list(lines)

    def readline(self) -> str:
        return self._lines.pop(0) if self._lines else ""


class _FakeStdout:
    def __init__(self) -> None:
        self.frames: list[str] = []

    def write(self, text: str) -> int:
        self.frames.append(text)
        return len(text)

    def flush(self) -> None:
        return None


def _build_tools(**overrides) -> EduAgentTools:
    deps: dict[str, object] = {
        "router": None,
        "profile": None,
        "doc": None,
        "quiz": None,
        "code": None,
        "media": None,
        "reading": None,
        "tutor": None,
        "wiki": None,
    }
    deps.update(overrides)
    return EduAgentTools(**deps)  # type: ignore[arg-type]


def _patch_mcp_infra(
    monkeypatch: pytest.MonkeyPatch,
    factory: async_sessionmaker,
    wiki=None,
) -> None:
    """把 MCP handler 内部用到的 DB池 / Wiki / 资产存储替换为测试桩。"""
    import app.core.database as database_module
    import app.core.storage as storage_module
    import app.wiki as wiki_module

    monkeypatch.setattr(database_module, "AsyncSessionLocal", factory)
    monkeypatch.setattr(
        wiki_module,
        "get_wiki_service",
        lambda session=None: wiki or _build_offline_wiki(),
    )
    monkeypatch.setattr(
        storage_module, "get_asset_storage", lambda: _StubAssetStorage()
    )


def test_tools_schema_has_16_tools_and_handler_parity() -> None:
    """工具数 16，schema 与 _handlers 一一对应，session_id 已改为可选。"""
    names = [tool["name"] for tool in TOOLS]
    assert len(names) == 16, f"工具数应为 16，实际 {len(names)}：{names}"
    assert "create_session" in names and "list_sessions" in names
    assert set(names) == set(_build_tools()._handlers)

    attach = next(t for t in TOOLS if t["name"] == "attach_material")
    assert attach["inputSchema"]["required"] == ["content"]
    search = next(t for t in TOOLS if t["name"] == "search_material")
    assert search["inputSchema"]["required"] == ["query"]

    for name in ("generate_quiz", "generate_code", "generate_reading"):
        schema = next(t for t in TOOLS if t["name"] == name)["inputSchema"]
        assert "session_id" in schema["properties"]
        assert "session_id" not in schema.get("required", [])


def test_get_or_create_default_session_is_idempotent() -> None:
    """默认会话按标题幂等：无则创建，有则复用最新一条。"""
    asyncio.run(_test_default_session_idempotent())


async def _test_default_session_idempotent() -> None:
    from app.core.database import Base
    from app.models.chat import ChatSession
    from app.services.chat_service import (
        DEFAULT_SESSION_TITLE,
        get_or_create_default_session,
    )

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as db:
            first = await get_or_create_default_session(db)
            second = await get_or_create_default_session(db)
            assert first.id == second.id, "默认会话应幂等复用，不应重复创建"
            assert first.title == DEFAULT_SESSION_TITLE

            # 多个同标题会话时取最新一条，且再次调用不漂移
            db.add(ChatSession(title=DEFAULT_SESSION_TITLE))
            await db.commit()
            newer = await get_or_create_default_session(db)
            assert newer.id > first.id
            assert (await get_or_create_default_session(db)).id == newer.id
    finally:
        await engine.dispose()


def test_attach_material_without_session_id_uses_default_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """省略 session_id 时自动挂载到默认会话，多次挂载复用同一会话。"""
    asyncio.run(_test_attach_default_session(monkeypatch))


async def _test_attach_default_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.database import Base
    from app.services.chat_service import DEFAULT_SESSION_TITLE, ChatService

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    shared_wiki = _build_offline_wiki()
    _patch_mcp_infra(monkeypatch, factory, wiki=shared_wiki)
    try:
        tools = _build_tools(wiki=shared_wiki)
        first = await tools.attach_material(content=MATERIAL_TEXT, filename="notes.md")
        second = await tools.attach_material(content="子网划分 掩码 计算方法。")
        assert first["session_id"] == second["session_id"]
        assert first["chunk_count"] >= 1

        default_id = first["session_id"]
        async with factory() as db:
            chat = await ChatService(session=db).get_session(default_id)
            assert chat is not None and chat.title == DEFAULT_SESSION_TITLE

        # 省略 session_id 的材料检索也应命中默认会话
        rows = await tools.search_material(query="TCP 三次握手")
        assert rows and all(r["course_id"] == f"session:{default_id}" for r in rows)
    finally:
        await engine.dispose()


def test_attach_material_with_missing_session_gives_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """显式传不存在的会话 → 报错文案含自救指引（省略/建会话）。"""
    asyncio.run(_test_attach_missing_session(monkeypatch))


async def _test_attach_missing_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    _patch_mcp_infra(monkeypatch, factory)
    try:
        tools = _build_tools()
        with pytest.raises(ValueError, match="可省略 session_id 使用默认会话"):
            await tools.attach_material(
                session_id=424242, content=MATERIAL_TEXT, filename="notes.md"
            )
        with pytest.raises(ValueError, match="或先调用 create_session 创建"):
            await tools.search_material(query="TCP", session_id=424242)
    finally:
        await engine.dispose()


def test_create_and_list_session_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_session 返回会话 id/标题；list_sessions 倒序限量 20 条。"""
    asyncio.run(_test_create_and_list_sessions(monkeypatch))


async def _test_create_and_list_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    _patch_mcp_infra(monkeypatch, factory)
    try:
        tools = _build_tools()
        created = await tools.create_session(title="专项复习")
        assert set(created) == {"session_id", "title"}
        assert created["title"] == "专项复习" and created["session_id"] > 0

        default_named = await tools.create_session()
        assert default_named["title"] == "新学习会话"

        # 造满 22 个会话，验证限量最近 20 条且按 id 倒序（最新一条是批量最后一个）
        for i in range(20):
            await tools.create_session(title=f"批量会话 {i}")
        rows = await tools.list_sessions()
        assert len(rows) == 20
        ids = [row["session_id"] for row in rows]
        assert ids == sorted(ids, reverse=True)
        assert ids[0] > default_named["session_id"]
        assert created["session_id"] not in ids  # 最早的会话已被限量挤出
        assert all(set(row) == {"session_id", "title", "created_at"} for row in rows)
        assert "T" in rows[0]["created_at"]  # ISO 时间戳
    finally:
        await engine.dispose()


def test_extract_profile_persist_saves_single_student_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """persist=true 时按单学生（user_id=1）把抽取结果经 ProfileService 落库。"""
    asyncio.run(_test_extract_profile_persist(monkeypatch))


async def _test_extract_profile_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import select

    from app.agents.profile_agent import ProfileAgent
    from app.core.database import Base
    from app.models.profile import StudentProfile

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    _patch_mcp_infra(monkeypatch, factory)
    try:
        tools = _build_tools(profile=ProfileAgent(llm_client=None))

        # 默认不落库：返回抽取更新本身
        update = await tools.extract_profile("我是计算机专业大一学生，每周能学10小时")
        assert update.get("major") == "计算机专业"
        assert "persisted" not in update

        result = await tools.extract_profile(
            "我是计算机专业大一学生，每周能学10小时", persist=True
        )
        assert result["persisted"] is True
        assert result["user_id"] == 1
        assert result["update"]["major"] == "计算机专业"

        async with factory() as db:
            row = (
                (
                    await db.execute(
                        select(StudentProfile).where(StudentProfile.user_id == 1)
                    )
                )
                .scalars()
                .first()
            )
            assert row is not None, "画像应已按单学生落库"
            assert row.major == "计算机专业"
            assert row.weekly_hours == 10
    finally:
        await engine.dispose()


def test_tutor_answer_parses_history_for_agent() -> None:
    """history 字符串解析为 role/content 列表后透传给 TutorAgent.answer。"""
    tutor = _StubTutor()
    tools = _build_tools(tutor=tutor)
    result = asyncio.run(
        tools.tutor_answer(
            question="继续", history="学生：什么是三次握手？\n助手：先看 SYN。"
        )
    )
    assert result == {"answer": "好的，我们继续。"}
    assert tutor.kwargs is not None
    assert tutor.kwargs["history"] == [
        {"role": "user", "content": "什么是三次握手？"},
        {"role": "assistant", "content": "先看 SYN。"},
    ]


def test_parse_history_handles_aliases_and_blanks() -> None:
    """说话人别名（中英文/大小写）、空行与无法识别行按学生发言兜底。"""
    history = "用户：hi\nAssistant: hello\nAI：ok\n\n普通一句"
    assert _parse_history(history) == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "普通一句"},
    ]
    assert _parse_history(None) == []
    assert _parse_history("") == []


def test_serve_stdio_replies_parse_error_frame_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """畸形 JSON 行回 -32700 错误帧，后续合法请求照常处理。"""
    asyncio.run(_test_parse_error_frame(monkeypatch))


async def _test_parse_error_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.mcp_server as mcp_module

    fake_in = _FakeStdin(
        [
            "{oops not json\n",
            json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}) + "\n",
        ]
    )
    fake_out = _FakeStdout()
    monkeypatch.setattr(sys, "stdin", fake_in)
    monkeypatch.setattr(sys, "stdout", fake_out)

    await mcp_module._serve_stdio(_build_tools())

    assert len(fake_out.frames) == 2, f"应恰好回两帧：{fake_out.frames}"
    first = json.loads(fake_out.frames[0])
    assert first["jsonrpc"] == "2.0"
    assert first["id"] is None
    assert first["error"]["code"] == -32700
    assert first["error"]["message"] == "Parse error"
    second = json.loads(fake_out.frames[1])
    assert second["id"] == 7 and second["result"] == {}


def test_parse_error_frame_shape() -> None:
    """-32700 帧构造器输出符合 JSON-RPC 规范。"""
    frame = _parse_error_frame(json.JSONDecodeError("Expecting value", "x", 0))
    assert frame["id"] is None
    assert frame["error"]["code"] == -32700
    assert frame["error"]["message"] == "Parse error"
    assert "data" in frame["error"]


def test_serve_stdio_replies_invalid_request_for_non_object_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """合法 JSON 但不是请求对象（数组行）回 -32600 帧，后续合法请求照常处理。"""
    asyncio.run(_test_invalid_request_frame(monkeypatch))


async def _test_invalid_request_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.mcp_server as mcp_module

    fake_in = _FakeStdin(
        [
            "[1, 2, 3]\n",
            json.dumps({"jsonrpc": "2.0", "id": 9, "method": "ping"}) + "\n",
        ]
    )
    fake_out = _FakeStdout()
    monkeypatch.setattr(sys, "stdin", fake_in)
    monkeypatch.setattr(sys, "stdout", fake_out)

    await mcp_module._serve_stdio(_build_tools())

    assert len(fake_out.frames) == 2, f"应恰好回两帧：{fake_out.frames}"
    first = json.loads(fake_out.frames[0])
    assert first["jsonrpc"] == "2.0"
    assert first["id"] is None
    assert first["error"]["code"] == -32600
    assert first["error"]["message"] == "Invalid Request"
    second = json.loads(fake_out.frames[1])
    assert second["id"] == 9 and second["result"] == {}
