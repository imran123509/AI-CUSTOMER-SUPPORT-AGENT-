import asyncio

import pytest

from app.core.circuit_breaker import CircuitBreaker, State
from app.core.exceptions import CircuitOpenError


@pytest.mark.asyncio
async def test_breaker_trips_and_recovers():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_seconds=0.1)

    async def boom():
        raise ConnectionError("nope")

    for _ in range(2):
        with pytest.raises(ConnectionError):
            await cb.call(boom)
    assert cb.state == State.OPEN

    with pytest.raises(CircuitOpenError):
        await cb.call(boom)

    await asyncio.sleep(0.15)

    async def ok():
        return 42

    res = await cb.call(ok)
    assert res == 42
    assert cb.state == State.CLOSED
