"""Async Redis client (cache, short-term memory, Redis Streams)."""
from __future__ import annotations

from typing import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import get_settings

_settings = get_settings()

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Returns a process-wide singleton Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            _settings.redis_url,
            decode_responses=True,
            health_check_interval=30,
        )
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


async def redis_dep() -> AsyncIterator[aioredis.Redis]:
    """FastAPI dependency."""
    yield await get_redis()
