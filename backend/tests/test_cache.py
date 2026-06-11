from __future__ import annotations

import asyncio

from app.core.cache import MemoryTTLCacheBackend, make_cache_key


def test_make_cache_key_is_stable_and_namespaced() -> None:
    key_a = make_cache_key("rag:search", "反向传播", 3, None)
    key_b = make_cache_key("rag:search", "反向传播", 3, None)
    key_c = make_cache_key("rag:search", "神经网络", 3, None)

    assert key_a == key_b
    assert key_a.startswith("rag:search:")
    assert key_a != key_c


def test_memory_ttl_cache_stores_values_and_evicts_oldest() -> None:
    asyncio.run(_test_memory_ttl_cache_stores_values_and_evicts_oldest())


async def _test_memory_ttl_cache_stores_values_and_evicts_oldest() -> None:
    cache = MemoryTTLCacheBackend(max_items=2)

    await cache.set("test:a", "A", ttl_seconds=60)
    await cache.set("test:b", "B", ttl_seconds=60)
    await cache.set("test:c", "C", ttl_seconds=60)

    assert await cache.get("test:a") is None
    assert await cache.get("test:b") == "B"
    assert await cache.get("test:c") == "C"

    await cache.clear_namespace("test")

    assert await cache.get("test:b") is None
    assert await cache.get("test:c") is None
