from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.chat import (
    ResourceCardPayload,
    SSEEvent,
    agent_status_event,
    done_event,
    error_event,
    profile_updated_event,
    resource_card_event,
    token_event,
)


async def _register_and_get_token(
    client: AsyncClient,
    username: str,
    password: str = "password123",
) -> str:
    response = await client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ── 端到端 API 测试（AsyncClient + ASGITransport）──────────────────────────


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_session_and_list(reset_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = await _register_and_get_token(ac, "session_list_user")

        resp = await ac.post(
            "/api/chat/session",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
        assert session_id > 0

        resp = await ac.get(
            "/api/chat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        sessions = resp.json()
        assert any(s["id"] == session_id for s in sessions)


@pytest.mark.asyncio
async def test_delete_session_requires_auth(reset_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete("/api/chat/sessions/1")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_session_success(reset_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = await _register_and_get_token(ac, "delete_success_user")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await ac.post("/api/chat/session", headers=headers)
        assert create_resp.status_code == 200
        session_id = create_resp.json()["session_id"]

        detail_resp = await ac.get(f"/api/chat/sessions/{session_id}", headers=headers)
        assert detail_resp.status_code == 200

        delete_resp = await ac.delete(
            f"/api/chat/sessions/{session_id}", headers=headers
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json() == {"success": True}

        detail_resp = await ac.get(f"/api/chat/sessions/{session_id}", headers=headers)
        assert detail_resp.status_code == 404

        list_resp = await ac.get("/api/chat/sessions", headers=headers)
        assert list_resp.status_code == 200
        assert all(session["id"] != session_id for session in list_resp.json())


@pytest.mark.asyncio
async def test_delete_session_returns_404_when_missing(reset_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = await _register_and_get_token(ac, "delete_missing_user")
        resp = await ac.delete(
            "/api/chat/sessions/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "会话不存在"


@pytest.mark.asyncio
async def test_delete_session_returns_404_for_other_user(reset_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_a = await _register_and_get_token(ac, "delete_owner_user")
        token_b = await _register_and_get_token(ac, "delete_other_user")
        owner_headers = {"Authorization": f"Bearer {token_a}"}
        other_headers = {"Authorization": f"Bearer {token_b}"}

        create_resp = await ac.post("/api/chat/session", headers=owner_headers)
        assert create_resp.status_code == 200
        session_id = create_resp.json()["session_id"]

        delete_resp = await ac.delete(
            f"/api/chat/sessions/{session_id}",
            headers=other_headers,
        )
        assert delete_resp.status_code == 404
        assert delete_resp.json()["detail"] == "会话不存在"

        detail_resp = await ac.get(
            f"/api/chat/sessions/{session_id}", headers=owner_headers
        )
        assert detail_resp.status_code == 200


@pytest.mark.asyncio
async def test_get_profile(reset_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = await _register_and_get_token(ac, "profile_api_user")
        resp = await ac.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data


# ── SSE 流式测试（TestClient + monkeypatch）───────────────────────────────


def _event_types_from_body(body: str) -> list[str]:
    event_types: list[str] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        data_line = next(
            (line for line in block.splitlines() if line.startswith("data: ")),
            None,
        )
        if data_line is None:
            continue
        payload = json.loads(data_line.removeprefix("data: "))
        event_types.append(payload["type"])
    return event_types


def _extract_session_ids(body: str) -> list[int]:
    session_ids: list[int] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        data_line = next(
            (line for line in block.splitlines() if line.startswith("data: ")),
            None,
        )
        if data_line is None:
            continue
        payload = json.loads(data_line.removeprefix("data: "))
        if payload.get("session_id") is not None:
            session_ids.append(payload["session_id"])
    return session_ids


def _resource_types_from_body(body: str) -> list[str]:
    resource_types: list[str] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        data_line = next(
            (line for line in block.splitlines() if line.startswith("data: ")),
            None,
        )
        if data_line is None:
            continue
        payload = json.loads(data_line.removeprefix("data: "))
        if payload["type"] == "resource_card":
            resource_types.append(payload["payload"]["resource_type"])
    return resource_types


async def _success_events(session_id: int) -> AsyncGenerator[SSEEvent, None]:
    yield agent_status_event(
        agent="ProfileAgent",
        status="working",
        message="正在更新学习画像",
        session_id=session_id,
    )
    yield profile_updated_event(session_id=session_id)

    yield agent_status_event(
        agent="DocAgent",
        status="working",
        message="正在生成学习文档",
        session_id=session_id,
    )
    yield token_event(token="反向传播讲义", session_id=session_id)
    yield resource_card_event(
        resource=ResourceCardPayload(
            id=1,
            resource_type="document",
            title="反向传播个性化学习讲义",
            content="这是讲义正文。",
            knowledge_point="反向传播",
            agent_name="DocAgent",
        ),
        session_id=session_id,
    )

    yield agent_status_event(
        agent="QuizAgent",
        status="working",
        message="正在生成练习题",
        session_id=session_id,
    )
    yield token_event(token="反向传播练习题", session_id=session_id)
    yield resource_card_event(
        resource=ResourceCardPayload(
            id=2,
            resource_type="quiz",
            title="反向传播练习题",
            content="这是练习题正文。",
            knowledge_point="反向传播",
            agent_name="QuizAgent",
        ),
        session_id=session_id,
    )

    yield agent_status_event(
        agent="CodeAgent",
        status="working",
        message="正在生成代码实践",
        session_id=session_id,
    )
    yield token_event(token="反向传播代码实践", session_id=session_id)
    yield resource_card_event(
        resource=ResourceCardPayload(
            id=3,
            resource_type="code",
            title="反向传播代码实践",
            content="这是代码实践正文。",
            knowledge_point="反向传播",
            agent_name="CodeAgent",
        ),
        session_id=session_id,
    )
    yield done_event(session_id=session_id)


async def _error_events(session_id: int) -> AsyncGenerator[SSEEvent, None]:
    yield agent_status_event(
        agent="DocAgent",
        status="working",
        message="正在生成学习文档",
        session_id=session_id,
    )
    yield token_event(token="反向传播讲义", session_id=session_id)
    yield resource_card_event(
        resource=ResourceCardPayload(
            id=1,
            resource_type="document",
            title="反向传播个性化学习讲义",
            content="这是讲义正文。",
            knowledge_point="反向传播",
            agent_name="DocAgent",
        ),
        session_id=session_id,
    )
    yield agent_status_event(
        agent="QuizAgent",
        status="working",
        message="正在生成练习题",
        session_id=session_id,
    )
    yield error_event(message="练习题生成失败", session_id=session_id)


class _StubOrchestrator:
    def __init__(self, event_factory):
        self._event_factory = event_factory

    async def run(
        self,
        *,
        session_id: int,
        user_message: str,
        user_id: int = 1,
        history: list | None = None,
        study_mode: bool = False,
        course_id: str | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        del user_message, user_id, history, study_mode, course_id
        async for event in self._event_factory(session_id):
            yield event


def test_chat_stream_returns_ordered_sse_events(client, monkeypatch) -> None:
    from app.api import chat as chat_api

    monkeypatch.setattr(
        chat_api,
        "build_orchestrator",
        lambda db_session: _StubOrchestrator(_success_events),
    )

    register_response = client.post(
        "/api/auth/register",
        json={"username": "stream_order_user", "password": "password123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    session_response = client.post("/api/chat/session", headers=headers)
    session_id = session_response.json()["session_id"]

    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "帮我复习反向传播"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    event_types = _event_types_from_body(response.text)
    assert event_types[-1] == "done"
    assert event_types.count("resource_card") == 3
    assert _resource_types_from_body(response.text) == ["document", "quiz", "code"]


def test_chat_stream_creates_session_when_session_id_missing(
    client, monkeypatch
) -> None:
    from app.api import chat as chat_api

    monkeypatch.setattr(
        chat_api,
        "build_orchestrator",
        lambda db_session: _StubOrchestrator(_success_events),
    )

    register_response = client.post(
        "/api/auth/register",
        json={"username": "stream_create_user", "password": "password123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]

    response = client.post(
        "/api/chat/stream",
        json={"message": "帮我复习反向传播", "course_id": "python_basics"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    session_ids = _extract_session_ids(response.text)
    assert session_ids
    assert all(session_id > 0 for session_id in session_ids)

    detail_response = client.get(
        f"/api/chat/sessions/{session_ids[0]}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["course_id"] == "python_basics"


def test_chat_stream_stops_after_error_event(client, monkeypatch) -> None:
    from app.api import chat as chat_api

    monkeypatch.setattr(
        chat_api,
        "build_orchestrator",
        lambda db_session: _StubOrchestrator(_error_events),
    )

    register_response = client.post(
        "/api/auth/register",
        json={"username": "stream_error_user", "password": "password123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    session_response = client.post("/api/chat/session", headers=headers)
    session_id = session_response.json()["session_id"]

    response = client.post(
        "/api/chat/stream",
        json={"session_id": session_id, "message": "帮我复习反向传播"},
        headers=headers,
    )

    assert response.status_code == 200
    event_types = _event_types_from_body(response.text)
    assert _resource_types_from_body(response.text) == ["document"]
    assert event_types[-1] == "error"
    assert "done" not in event_types
