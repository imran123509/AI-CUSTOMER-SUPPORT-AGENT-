"""Redis Streams event bus.

Producers push events with `publish(stream, event)`; consumers (workers in
`app.workers`) read with `consume(stream, group, consumer)`.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


async def publish(stream: str, event: dict[str, Any]) -> str:
    redis = await get_redis()
    payload = {
        "id": str(uuid.uuid4()),
        "data": json.dumps(event, default=str),
    }
    msg_id = await redis.xadd(stream, payload, maxlen=10_000, approximate=True)
    logger.debug("event.published", stream=stream, msg_id=msg_id)
    return msg_id


async def ensure_group(stream: str, group: str) -> None:
    """Create the consumer group, starting at the oldest retained entry.

    The start id must be "0", not "$".  "$" anchors a brand-new group to the
    tail of the stream, so anything published before the worker first ran is
    never delivered -- a document uploaded while the worker was down stayed
    PENDING forever with no error anywhere.  Starting at "0" makes the group
    drain the retained backlog, which is what a durable work queue owes its
    producers.  Creation happens once; an existing group keeps its own
    last-delivered-id and is untouched (BUSYGROUP below).
    """
    redis = await get_redis()
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception as exc:  # group already exists is fine
        if "BUSYGROUP" not in str(exc):
            raise


async def consume(
    stream: str,
    group: str,
    consumer: str,
    *,
    block_ms: int = 5000,
    count: int = 10,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Async generator yielding (msg_id, payload) tuples.

    The caller is responsible for acknowledging messages with `ack`.
    """
    redis = await get_redis()
    await ensure_group(stream, group)
    while True:
        resp = await redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )
        if not resp:
            continue
        for _stream, messages in resp:
            for msg_id, fields in messages:
                try:
                    data = json.loads(fields.get("data", "{}"))
                except Exception:
                    data = {}
                yield msg_id, data


async def ack(stream: str, group: str, msg_id: str) -> None:
    redis = await get_redis()
    await redis.xack(stream, group, msg_id)
