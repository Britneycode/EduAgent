from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


@dataclass(frozen=True, slots=True)
class StoredAsset:
    key: str
    url: str
    path: Path
    filename: str
    media_type: str
    size_bytes: int


class LocalAssetStorage:
    """本地资产存储抽象，后续可替换为 MinIO/S3 实现。"""

    def __init__(self, base_dir: str | Path, public_url_prefix: str = "/api/assets"):
        self.base_dir = Path(base_dir).resolve()
        self.public_url_prefix = public_url_prefix.rstrip("/")

    def save_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        media_type: str,
        namespace: str = "resources",
    ) -> StoredAsset:
        safe_namespace = _sanitize_path_part(namespace)
        safe_filename = _sanitize_filename(filename)
        stored_filename = f"{uuid4().hex}-{safe_filename}"
        relative_path = Path(safe_namespace) / stored_filename
        target_path = (self.base_dir / relative_path).resolve()
        if not _is_relative_to(target_path, self.base_dir):
            raise ValueError("资产路径越界")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        key = relative_path.as_posix()
        return StoredAsset(
            key=key,
            url=f"{self.public_url_prefix}/{key}",
            path=target_path,
            filename=safe_filename,
            media_type=media_type,
            size_bytes=len(data),
        )

    def resolve(self, key: str) -> Path | None:
        safe_key = key.replace("\\", "/").lstrip("/")
        target_path = (self.base_dir / safe_key).resolve()
        if not _is_relative_to(target_path, self.base_dir):
            return None
        if not target_path.is_file():
            return None
        return target_path


@lru_cache
def get_asset_storage() -> LocalAssetStorage:
    settings = get_settings()
    return LocalAssetStorage(
        base_dir=settings.asset_storage_dir,
        public_url_prefix=settings.asset_public_url_prefix,
    )


def _sanitize_filename(filename: str) -> str:
    name = Path(filename or "asset.bin").name.strip()
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name) or "asset.bin"


def _sanitize_path_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()) or "assets"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
