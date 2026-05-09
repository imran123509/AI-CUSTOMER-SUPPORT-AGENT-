"""Worker: consumes the events stream and updates Redis-cached counters."""
from __future__ import annotations

from app.core.events import ack, consume
from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)
STREAM = "unfyd:events"
GROUP = "event-aggregators"
CONSUMER = "agg-1"


async def run() -> None:
    redis = await get_redis()
    async for msg_id, event in consume(STREAM, GROUP, CONSUMER):
        try:
            org = event.get("organization_id")
            etype = event.get("type", "")
            if not org:
                continue
            day_key = f"metrics:{org}:{etype}:day"
            await redis.incr(day_key)
            await redis.expire(day_key, 86_400 * 31)
            if etype == "ai.message" and event.get("latency_ms"):
                lat_key = f"metrics:{org}:ai_latency_ms"
                await redis.lpush(lat_key, int(event["latency_ms"]))
                await redis.ltrim(lat_key, 0, 999)
        except Exception as exc:
            logger.exception("event_aggregator.failed", error=str(exc))
        finally:
            await ack(STREAM, GROUP, msg_id)
