from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import AsyncSessionLocal
from app.services.profile_service import ProfileService


async def _register_and_get_auth(
    client: AsyncClient,
    username: str,
    password: str = "password123",
) -> tuple[str, int]:
    response = await client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"], data["user_id"]


@pytest.mark.asyncio
async def test_profile_endpoint_returns_current_profile(reset_database) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await _register_and_get_auth(client, "profile_current_user")

        async with AsyncSessionLocal() as session:
            from app.services.chat_service import ChatService

            chat_service = ChatService(session=session)
            profile_service = ProfileService(session=session)
            session_id = await chat_service.create_session(user_id=user_id)
            await profile_service.save_profile_update(
                session_id,
                {
                    "major": "计算机专业",
                    "knowledge_base": {"机器学习": "基础"},
                },
            )

        response = await client.get(
            f"/api/profile?session_id={session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["major"] == "计算机专业"
    assert "knowledge_base" in data


@pytest.mark.asyncio
async def test_profile_endpoint_keeps_user_scoped_when_session_id_missing(
    reset_database,
) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _register_and_get_auth(client, "profile_missing_session_user")
        response = await client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        sessions_response = await client.get(
            "/api/chat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is None
    assert "major" in data
    assert sessions_response.status_code == 200
    assert sessions_response.json() == []


@pytest.mark.asyncio
async def test_profile_endpoint_allows_direct_edit_and_clear(
    reset_database,
) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _user_id = await _register_and_get_auth(client, "profile_edit_user")

        response = await client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "major": "  人工智能  ",
                "grade": "大二",
                "knowledge_base": {" 机器学习 ": "入门", "": "忽略"},
                "weak_points": ["反向传播", "反向传播", " "],
                "interest_areas": ["NLP", "CV"],
                "weekly_hours": 8,
            },
        )
        clear_response = await client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "major": None,
                "weak_points": [],
                "knowledge_base": {},
                "weekly_hours": None,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["major"] == "人工智能"
    assert data["knowledge_base"] == {"机器学习": "入门"}
    assert data["weak_points"] == ["反向传播"]
    assert data["weekly_hours"] == 8

    assert clear_response.status_code == 200
    cleared = clear_response.json()
    assert cleared["major"] is None
    assert cleared["weak_points"] == []
    assert cleared["knowledge_base"] == {}
    assert cleared["weekly_hours"] is None


@pytest.mark.asyncio
async def test_profile_history_endpoint_returns_snapshots(
    reset_database,
) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _user_id = await _register_and_get_auth(client, "profile_history_user")

        await client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"major": "人工智能", "grade": "大三"},
        )
        await client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"weak_points": ["搜索算法"]},
        )

        response = await client.get(
            "/api/profile/history?limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["source"] == "manual"
    assert items[0]["changed_fields"] == ["weak_points"]
    assert items[0]["profile_data"]["weak_points"] == ["搜索算法"]
    assert set(items[1]["changed_fields"]) == {"grade", "major"}
