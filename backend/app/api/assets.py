from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.storage import get_asset_storage
from app.models.user import User
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/assets", tags=["assets"])
_RESOURCE_ASSET_PATTERN = re.compile(r"^resource-(?P<resource_id>\d+)/.+")


@router.get("/{asset_key:path}")
async def get_asset(
    asset_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    match = _RESOURCE_ASSET_PATTERN.match(asset_key.replace("\\", "/").lstrip("/"))
    if match is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    resource_id = int(match.group("resource_id"))
    resource = await ChatService(session=db).get_resource(resource_id, user_id=user.id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    storage = get_asset_storage()
    path = storage.resolve(asset_key)
    if path is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return FileResponse(path)
