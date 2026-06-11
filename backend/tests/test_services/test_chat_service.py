from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_create_session(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session()
    assert isinstance(session_id, int)
    assert session_id > 0


@pytest.mark.asyncio
async def test_create_session_persists_course_id(async_session: AsyncSession):
    service = ChatService(session=async_session)

    session_id = await service.create_session(course_id="python_basics")

    session = await service.get_session(session_id)
    assert session is not None
    assert session.course_id == "python_basics"


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
    msg = await service.save_message(session_id, "user", "你好", turn_id="turn-1")
    assert msg.role == "user"
    assert msg.content == "你好"
    assert msg.turn_id == "turn-1"
    messages = await service.list_messages(session_id)
    assert len(messages) == 1
    assert messages[0].turn_id == "turn-1"


@pytest.mark.asyncio
async def test_save_and_list_resources(async_session: AsyncSession):
    service = ChatService(session=async_session)
    session_id = await service.create_session()
    resource = await service.save_resource(
        session_id=session_id,
        resource_type="document",
        title="测试文档",
        content="内容",
        turn_id="turn-2",
    )
    assert resource.id is not None
    assert resource.turn_id == "turn-2"
    resources = await service.list_resources(session_id)
    assert len(resources) == 1
    assert resources[0].turn_id == "turn-2"


@pytest.mark.asyncio
async def test_list_sessions(async_session: AsyncSession):
    user = User(username="session_list_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    service = ChatService(session=async_session)
    await service.create_session("会话A", user_id=user.id)
    await service.create_session("会话B", user_id=user.id)
    sessions = await service.list_sessions(user_id=user.id)
    assert len(sessions) == 2


@pytest.mark.asyncio
async def test_update_session_title(async_session: AsyncSession):
    user = User(username="rename_user", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    service = ChatService(session=async_session)
    session_id = await service.create_session("旧标题", user_id=user.id)
    await service.update_session_title(session_id, "新标题", user_id=user.id)
    session = await service.get_session(session_id, user_id=user.id)
    assert session is not None
    assert session.title == "新标题"


@pytest.mark.asyncio
async def test_delete_session_removes_messages_and_resources(
    async_session: AsyncSession,
):
    service = ChatService(session=async_session)
    session_id = await service.create_session("待删除会话")
    await service.save_message(session_id, "user", "你好")
    await service.save_resource(
        session_id=session_id,
        resource_type="document",
        title="测试文档",
        content="内容",
    )

    deleted = await service.delete_session(session_id)

    assert deleted is True
    assert await service.get_session(session_id) is None
    assert await service.list_messages(session_id) == []
    assert await service.list_resources(session_id) == []


@pytest.mark.asyncio
async def test_delete_session_returns_false_when_missing(async_session: AsyncSession):
    service = ChatService(session=async_session)

    deleted = await service.delete_session(99999)

    assert deleted is False


@pytest.mark.asyncio
async def test_delete_session_respects_user_scope(async_session: AsyncSession):
    user_a = User(username="user_a", hashed_password="hashed")
    user_b = User(username="user_b", hashed_password="hashed")
    async_session.add_all([user_a, user_b])
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    service = ChatService(session=async_session)
    session_id = await service.create_session("用户A会话", user_id=user_a.id)

    deleted = await service.delete_session(session_id, user_id=user_b.id)

    assert deleted is False
    assert await service.get_session(session_id, user_id=user_a.id) is not None
