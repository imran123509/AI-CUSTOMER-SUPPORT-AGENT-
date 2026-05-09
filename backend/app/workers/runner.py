"""Worker runner — fans out across multiple stream consumers.

Run with: `python -m app.workers.runner`.
"""
from __future__ import annotations

import asyncio
import signal
from typing import Awaitable, Callable

from app.core.logging import configure_logging, get_logger
from app.workers.document_processor import run as run_doc_worker
from app.workers.event_aggregator import run as run_event_worker
from app.workers.sla_monitor import run as run_sla_worker

configure_logging()
logger = get_logger(__name__)


async def _supervised(name: str, coro_factory: Callable[[], Awaitable[None]]) -> None:
    """Restart a worker forever; exponential backoff on crash."""
    delay = 1.0
    while True:
        try:
            logger.info("worker.start", name=name)
            await coro_factory()
            return
        except asyncio.CancelledError:
            logger.info("worker.cancelled", name=name)
            return
        except Exception as exc:
            logger.exception("worker.crash", name=name, error=str(exc))
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


async def main() -> None:
    stop_event = asyncio.Event()

    def _stop(*_a):
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:  # Windows
            signal.signal(sig, _stop)

    tasks = [
        asyncio.create_task(_supervised("doc_processor", run_doc_worker)),
        asyncio.create_task(_supervised("event_aggregator", run_event_worker)),
        asyncio.create_task(_supervised("sla_monitor", run_sla_worker)),
    ]
    await stop_event.wait()
    logger.info("worker.shutdown")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
