from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.profile import (
    ProfileHistoryItem,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    session_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    profile_service = ProfileService(session=db)

    return await profile_service.get_or_create_profile(
        session_id=session_id,
        user_id=user.id,
    )


@router.get("/history", response_model=list[ProfileHistoryItem])
async def get_profile_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProfileHistoryItem]:
    profile_service = ProfileService(session=db)
    return await profile_service.list_profile_history(user_id=user.id, limit=limit)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    session_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    profile_service = ProfileService(session=db)

    update = request.model_dump(exclude_unset=True)
    return await profile_service.update_profile_direct(
        user_id=user.id,
        session_id=session_id,
        update=update,
    )
