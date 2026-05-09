"""Sliding-window rate limiter backed by Redis.

Used as a FastAPI dependency on heavy/AI endpoints to protect upstream
services and our own quota.
"""
from __future__ import annotations

import time

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError
from app.core.redis import get_redis

_settings = get_settings()


class RateLimiter:
    def __init__(self, *, per_minute: int | None = None, key_prefix: str = "rl"):
        self.per_minute = per_minute or _settings.rate_limit_per_minute
        self.key_prefix = key_prefix
        self.window = 60

    async def __call__(self, request: Request) -> None:
        identifier = self._identifier(request)
        redis = await get_redis()
        now = int(time.time())
        bucket = now // self.window
        key = f"{self.key_prefix}:{identifier}:{bucket}"
        pipe = redis.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, self.window * 2)
        count, _ = await pipe.execute()
        if int(count) > self.per_minute:
            raise RateLimitedError(
                f"Rate limit exceeded ({self.per_minute}/min)",
                status_code=429,
            )

    @staticmethod
    def _identifier(request: Request) -> str:
        # Prefer authenticated subject, fall back to IP
        user = getattr(request.state, "user", None)
        if user is not None:
            return f"user:{user.id}"
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "anon")
        return f"ip:{ip.split(',')[0].strip()}"
