from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.chat import ChatSession


@pytest.mark.asyncio
async def test_create_tables_and_insert_session(reset_database) -> None:
    async with AsyncSessionLocal() as session:
        item = ChatSession(title="首次学习会话")
        session.add(item)
        await session.commit()
        rows = (await session.execute(select(ChatSession))).scalars().all()
        assert len(rows) == 1
