"""Conversation memory.

Layers:
- Short-term: Redis list keyed by conversation id, rolling window of N msgs.
- Long-term: PostgreSQL `messages` (canonical) + `conversation.summary`.
- Compression: when a conversation grows past the window, summarise older
  turns and replace them with the summary in short-term memory.
"""
from __future__ import annotations

import json
from typing import List

from app.core.config import get_settings
from app.core.redis import get_redis

settings = get_settings()

WINDOW_SIZE = 24  # number of recent message turns kept hot in Redis


def _key(conversation_id: str) -> str:
    return f"conv:mem:{conversation_id}"


async def append_turn(conversation_id: str, role: str, content: str) -> None:
    redis = await get_redis()
    payload = json.dumps({"role": role, "content": content})
    pipe = redis.pipeline()
    pipe.rpush(_key(conversation_id), payload)
    pipe.ltrim(_key(conversation_id), -WINDOW_SIZE, -1)
    pipe.expire(_key(conversation_id), settings.redis_memory_ttl_seconds)
    await pipe.execute()


async def get_window(conversation_id: str) -> List[dict]:
    redis = await get_redis()
    raw = await redis.lrange(_key(conversation_id), 0, -1)
    out: List[dict] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except Exception:
            continue
    return out


async def clear(conversation_id: str) -> None:
    redis = await get_redis()
    await redis.delete(_key(conversation_id))


async def replace_with_summary(conversation_id: str, summary: str) -> None:
    redis = await get_redis()
    pipe = redis.pipeline()
    pipe.delete(_key(conversation_id))
    pipe.rpush(
        _key(conversation_id),
        json.dumps({"role": "system", "content": f"Summary of earlier turns: {summary}"}),
    )
    pipe.expire(_key(conversation_id), settings.redis_memory_ttl_seconds)
    await pipe.execute()


# ----------------------- user-preference memory ---------------------------
async def set_user_pref(user_id: str, key: str, value: str) -> None:
    redis = await get_redis()
    await redis.hset(f"user:pref:{user_id}", key, value)


async def get_user_prefs(user_id: str) -> dict:
    redis = await get_redis()
    return await redis.hgetall(f"user:pref:{user_id}")
