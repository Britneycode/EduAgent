from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    name: str

    async def get(self, key: str) -> str | None:
        """读取缓存字符串。"""

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """写入带 TTL 的缓存字符串。"""

    async def clear_namespace(self, namespace: str) -> None:
        """清理指定命名空间下的缓存。"""

    async def close(self) -> None:
        """释放连接资源。"""


class NullCacheBackend:
    name = "disabled"

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    async def clear_namespace(self, namespace: str) -> None:
        return None

    async def close(self) -> None:
        return None


class MemoryTTLCacheBackend:
    name = "memory"

    def __init__(self, max_items: int = 512) -> None:
        self._max_items = max_items
        self._items: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> str | None:
        item = self._items.get(key)
        if item is None:
            return None

        expires_at, value = item
        if expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._prune_expired()
        if len(self._items) >= self._max_items:
            oldest_key = min(self._items, key=lambda item_key: self._items[item_key][0])
            self._items.pop(oldest_key, None)
        self._items[key] = (time.monotonic() + max(1, ttl_seconds), value)

    async def clear_namespace(self, namespace: str) -> None:
        prefix = f"{namespace}:"
        for key in list(self._items):
            if key.startswith(prefix):
                self._items.pop(key, None)

    async def close(self) -> None:
        self._items.clear()

    def _prune_expired(self) -> None:
        now = time.monotonic()
        for key, (expires_at, _value) in list(self._items.items()):
            if expires_at <= now:
                self._items.pop(key, None)


class RedisCacheBackend:
    name = "redis"

    def __init__(self, redis_url: str) -> None:
        from redis.asyncio import Redis

        self._client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def get(self, key: str) -> str | None:
        value = await self._client.get(key)
        return value if isinstance(value, str) else None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._client.set(key, value, ex=max(1, ttl_seconds))

    async def clear_namespace(self, namespace: str) -> None:
        pattern = f"{namespace}:*"
        batch: list[str] = []
        async for key in self._client.scan_iter(match=pattern, count=200):
            batch.append(key)
            if len(batch) >= 200:
                await self._client.delete(*batch)
                batch.clear()
        if batch:
            await self._client.delete(*batch)

    async def close(self) -> None:
        await self._client.aclose()


@dataclass(slots=True)
class CacheStatus:
    enabled: bool
    backend: str
    redis_configured: bool


_cache_backend: CacheBackend | None = None


def make_cache_key(namespace: str, *parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def get_cache_backend() -> CacheBackend:
    global _cache_backend
    if _cache_backend is not None:
        return _cache_backend

    settings = get_settings()
    if not settings.cache_enabled:
        _cache_backend = NullCacheBackend()
        return _cache_backend

    if settings.redis_url:
        try:
            _cache_backend = RedisCacheBackend(settings.redis_url)
            return _cache_backend
        except Exception:
            logger.warning("Redis 缓存初始化失败，回退内存缓存", exc_info=True)

    _cache_backend = MemoryTTLCacheBackend(max_items=settings.cache_memory_max_items)
    return _cache_backend


async def close_cache_backend() -> None:
    global _cache_backend
    if _cache_backend is not None:
        await _cache_backend.close()
        _cache_backend = None


def get_cache_status() -> CacheStatus:
    settings = get_settings()
    backend = get_cache_backend()
    return CacheStatus(
        enabled=settings.cache_enabled,
        backend=backend.name,
        redis_configured=bool(settings.redis_url),
    )
