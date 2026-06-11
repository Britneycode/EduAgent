from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.storage import get_asset_storage

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/{asset_key:path}")
async def get_asset(asset_key: str) -> FileResponse:
    storage = get_asset_storage()
    path = storage.resolve(asset_key)
    if path is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return FileResponse(path)
