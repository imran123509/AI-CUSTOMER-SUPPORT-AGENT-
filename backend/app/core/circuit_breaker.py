"""Lightweight in-process circuit breaker.

Wraps calls to external dependencies (Gemini, ChromaDB).  Tracks consecutive
failures, trips when a threshold is reached, and re-closes after a cool-down
period.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, TypeVar

from app.core.exceptions import CircuitOpenError
from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_seconds: float = 30.0
    state: State = State.CLOSED
    failures: int = 0
    opened_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        async with self._lock:
            if self.state == State.OPEN:
                if time.time() - self.opened_at >= self.recovery_seconds:
                    self.state = State.HALF_OPEN
                    logger.info("circuit_breaker.half_open", name=self.name)
                else:
                    raise CircuitOpenError(f"Circuit '{self.name}' open")

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            await self._on_failure(exc)
            raise
        else:
            await self._on_success()
            return result

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = State.OPEN
                self.opened_at = time.time()
                logger.warning(
                    "circuit_breaker.opened",
                    name=self.name,
                    error=str(exc),
                    failures=self.failures,
                )

    async def _on_success(self) -> None:
        async with self._lock:
            if self.state == State.HALF_OPEN:
                logger.info("circuit_breaker.closed", name=self.name)
            self.state = State.CLOSED
            self.failures = 0
            self.opened_at = 0.0


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _breakers[name]
