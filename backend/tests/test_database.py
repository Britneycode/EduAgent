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
async def test_async_session_local():
    """AsyncSessionLocal 应该能创建可用的会话。"""
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
