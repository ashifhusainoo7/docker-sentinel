import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from src.worker.main import _consume_tenant


@pytest.mark.asyncio
async def test_acks_only_after_successful_process():
    tid = uuid.uuid4()
    shutdown = asyncio.Event()
    event = {"id": "1-0", "docker_host_id": str(uuid.uuid4())}

    calls = {"n": 0}

    async def fake_consume(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return [event]
        shutdown.set()  # second cycle: stop the loop
        return []

    with (
        patch("src.services.redis_stream.consume_crash_events", side_effect=fake_consume),
        patch("src.services.redis_stream.ack_crash_event", new=AsyncMock()) as ack,
        patch("src.worker.main._process_event", new=AsyncMock()) as proc,
    ):
        await _consume_tenant(tid, shutdown)

    proc.assert_awaited_once()
    ack.assert_awaited_once_with(str(tid), "1-0", "orchestrator")


@pytest.mark.asyncio
async def test_does_not_ack_when_processing_raises():
    tid = uuid.uuid4()
    shutdown = asyncio.Event()
    event = {"id": "7-0", "docker_host_id": str(uuid.uuid4())}

    async def proc_raise(*_a, **_k):
        shutdown.set()  # ensure the backoff wait returns immediately
        raise RuntimeError("db insert failed")

    with (
        patch(
            "src.services.redis_stream.consume_crash_events",
            new=AsyncMock(return_value=[event]),
        ),
        patch("src.services.redis_stream.ack_crash_event", new=AsyncMock()) as ack,
        patch("src.worker.main._process_event", side_effect=proc_raise),
    ):
        await _consume_tenant(tid, shutdown)

    # Processing failed → message left pending (not acked) for later reclaim.
    ack.assert_not_awaited()


@pytest.mark.asyncio
async def test_resets_redis_on_connection_error():
    tid = uuid.uuid4()
    shutdown = asyncio.Event()

    async def consume_conn_err(*_a, **_k):
        shutdown.set()
        raise RedisConnectionError("redis down")

    with (
        patch(
            "src.services.redis_stream.consume_crash_events",
            side_effect=consume_conn_err,
        ),
        patch("src.services.redis_stream.reset_redis", new=AsyncMock()) as reset,
    ):
        await _consume_tenant(tid, shutdown)

    reset.assert_awaited_once()
