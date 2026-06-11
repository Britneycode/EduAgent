from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession) -> None:
    user = User(
        username="testuser", hashed_password="fakehash", display_name="测试用户"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.display_name == "测试用户"


@pytest.mark.asyncio
async def test_username_unique(async_session: AsyncSession) -> None:
    user1 = User(username="dup", hashed_password="hash1")
    async_session.add(user1)
    await async_session.commit()

    user2 = User(username="dup", hashed_password="hash2")
    async_session.add(user2)
    with pytest.raises(Exception):
        await async_session.commit()


def test_password_hash_and_verify() -> None:
    password = "mypassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token() -> None:
    token = create_access_token(user_id=42)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"


def test_decode_invalid_token() -> None:
    payload = decode_access_token("invalid.token.here")
    assert payload is None


@pytest.mark.asyncio
async def test_register_success() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "password123",
                "display_name": "新用户",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] > 0


@pytest.mark.asyncio
async def test_register_short_password_returns_friendly_error() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/register",
            json={
                "username": "shortpass",
                "password": "12345",
            },
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_duplicate_username() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/auth/register",
            json={
                "username": "dupuser",
                "password": "pass123456",
            },
        )
        resp = await client.post(
            "/api/auth/register",
            json={
                "username": "dupuser",
                "password": "pass234567",
            },
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "password": "mypass123",
            },
        )
        resp = await client.post(
            "/api/auth/login",
            json={
                "username": "loginuser",
                "password": "mypass123",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/auth/register",
            json={
                "username": "wrongpass",
                "password": "correct1",
            },
        )
        resp = await client.post(
            "/api/auth/login",
            json={
                "username": "wrongpass",
                "password": "incorrect",
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_returns_new_access_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/auth/register",
            json={"username": "refresh_user", "password": "password123"},
        )
        token = reg.json()["access_token"]
        resp = await client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["access_token"] != token
    assert data["user_id"] == reg.json()["user_id"]


@pytest.mark.asyncio
async def test_change_password_requires_current_password_and_allows_new_login() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/auth/register",
            json={"username": "change_password_user", "password": "oldpass123"},
        )
        token = reg.json()["access_token"]
        wrong = await client.post(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "badpass", "new_password": "newpass123"},
        )
        changed = await client.post(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "oldpass123", "new_password": "newpass123"},
        )
        old_login = await client.post(
            "/api/auth/login",
            json={"username": "change_password_user", "password": "oldpass123"},
        )
        new_login = await client.post(
            "/api/auth/login",
            json={"username": "change_password_user", "password": "newpass123"},
        )

    assert wrong.status_code == 400
    assert changed.status_code == 200
    assert old_login.status_code == 401
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_chat_sessions_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chat/sessions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_sessions_with_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/auth/register",
            json={
                "username": "chatuser",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        resp = await client.get(
            "/api/chat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_chat_session_data_isolation() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg1 = await client.post(
            "/api/auth/register",
            json={
                "username": "user_a",
                "password": "password123",
            },
        )
        token_a = reg1.json()["access_token"]

        reg2 = await client.post(
            "/api/auth/register",
            json={
                "username": "user_b",
                "password": "password123",
            },
        )
        token_b = reg2.json()["access_token"]

        resp_a = await client.post(
            "/api/chat/session",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.status_code == 200

        resp_b = await client.get(
            "/api/chat/sessions",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0


@pytest.mark.asyncio
async def test_profile_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/profile")
    assert resp.status_code == 403 or resp.status_code == 401


@pytest.mark.asyncio
async def test_profile_with_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/auth/register",
            json={
                "username": "profileuser",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        resp = await client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] > 0
