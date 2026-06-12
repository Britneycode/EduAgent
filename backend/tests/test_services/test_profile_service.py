from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.profile_service import ProfileService


@pytest.mark.asyncio
async def test_get_or_create_profile(async_session: AsyncSession):
    service = ProfileService(session=async_session)
    profile = await service.get_or_create_profile(session_id=1)
    assert profile.user_id == 1
    assert profile.session_id == 1


@pytest.mark.asyncio
async def test_save_profile_update(async_session: AsyncSession):
    service = ProfileService(session=async_session)
    await service.get_or_create_profile(session_id=1)
    updated = await service.save_profile_update(
        session_id=1,
        update={"major": "计算机科学", "grade": "大三"},
    )
    assert updated.major == "计算机科学"
    assert updated.grade == "大三"


@pytest.mark.asyncio
async def test_profile_merge_accumulates(async_session: AsyncSession):
    service = ProfileService(session=async_session)
    await service.get_or_create_profile(session_id=1)
    await service.save_profile_update(1, {"major": "计算机"})
    result = await service.save_profile_update(1, {"grade": "大二"})
    assert result.major == "计算机"
    assert result.grade == "大二"


@pytest.mark.asyncio
async def test_profile_history_records_agent_and_manual_snapshots(
    async_session: AsyncSession,
):
    service = ProfileService(session=async_session)
    await service.get_or_create_profile(session_id=1)

    await service.save_profile_update(1, {"major": "计算机"})
    await service.update_profile_direct(
        user_id=1,
        session_id=1,
        update={"grade": "大二", "weak_points": ["反向传播"]},
    )

    history = await service.list_profile_history(user_id=1)

    assert len(history) == 2
    assert history[0].source == "manual"
    assert set(history[0].changed_fields) == {"grade", "weak_points"}
    assert history[0].profile_data["grade"] == "大二"
    assert history[1].source == "agent"
    assert history[1].changed_fields == ["major"]


@pytest.mark.asyncio
async def test_preview_profile_update_does_not_persist_candidate(
    async_session: AsyncSession,
):
    service = ProfileService(session=async_session)

    current, proposed, changed_fields = await service.preview_profile_update(
        user_id=1,
        session_id=7,
        update={"major": "计算机", "weak_points": ["反向传播"]},
    )
    history = await service.list_profile_history(user_id=1)
    profile = await service.get_or_create_profile(session_id=7, user_id=1)

    assert current.major is None
    assert proposed == {"major": "计算机", "weak_points": ["反向传播"]}
    assert set(changed_fields) == {"major", "weak_points"}
    assert history == []
    assert profile.major is None
    assert profile.weak_points == []


@pytest.mark.asyncio
async def test_merge_profile_logic():
    service = ProfileService(session=None)
    existing = {"major": "数学", "grade": None, "knowledge_base": {}, "weak_points": []}
    update = {"grade": "大一", "weak_points": ["线性代数"]}
    merged = service.merge_profile(existing, update)
    assert merged["major"] == "数学"
    assert merged["grade"] == "大一"
    assert merged["weak_points"] == ["线性代数"]


@pytest.mark.asyncio
async def test_merge_profile_normalizes_and_accumulates_knowledge_base():
    service = ProfileService(session=None)
    existing = {
        "major": "数学",
        "knowledge_base": {"线性代数": "掌握"},
        "weak_points": [],
    }
    update = {"knowledge_base": {"subject": "机器学习", "level": "一般"}}

    merged = service.merge_profile(existing, update)

    assert merged["knowledge_base"] == {
        "线性代数": "掌握",
        "机器学习": "一般",
    }


@pytest.mark.asyncio
async def test_merge_profile_accumulates_unique_weak_points():
    service = ProfileService(session=None)
    existing = {"weak_points": ["线性代数"], "knowledge_base": {}}
    update = {"weak_points": ["线性代数", "反向传播"]}

    merged = service.merge_profile(existing, update)

    assert merged["weak_points"] == ["线性代数", "反向传播"]
