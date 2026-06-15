"""Integration tests for the Redis crash-event consumer against a real Redis.

These exercise XAUTOCLAIM / xreadgroup / xack semantics that mocks cannot verify.
Run with the live stack up (``docker compose up -d redis``):

    PYTHONPATH=. py -3.12 -m pytest tests/integration -v -m integration

Skipped automatically if Redis is unreachable.
"""

import uuid

import pytest

from src.services import redis_stream
from src.services.redis_stream import (
    ack_crash_event,
    consume_crash_events,
    get_redis,
    publish_crash_event,
    reset_redis,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_env():
    """Provide a live client + a unique tenant/group, skipping if Redis is down."""
    try:
        r = await get_redis()
        await r.ping()
    except Exception as exc:  # pragma: no cover - depends on environment
        pytest.skip(f"Redis not reachable: {exc}")

    tenant = str(uuid.uuid4())
    group = f"itest-{uuid.uuid4().hex[:8]}"
    stream_key = f"crashes:{tenant}"

    yield r, tenant, group, stream_key

    # Cleanup so reruns stay clean.
    try:
        await r.delete(stream_key)
    except Exception:
        pass
    await reset_redis()


def _payload(name="web-1"):
    return {"docker_host_id": str(uuid.uuid4()), "container_name": name, "exit_code": 137}


@pytest.mark.asyncio
async def test_consume_leaves_message_pending_until_acked(redis_env):
    r, tenant, group, stream_key = redis_env

    await publish_crash_event(tenant, _payload())
    events = await consume_crash_events(tenant, consumer_group=group)

    assert len(events) == 1
    msg_id = events[0]["id"]
    assert events[0]["container_name"] == "web-1"

    # Read but not acked -> still pending (survives a crash, can be reclaimed).
    summary = await r.xpending(stream_key, group)
    assert summary["pending"] == 1

    await ack_crash_event(tenant, msg_id, group)

    summary = await r.xpending(stream_key, group)
    assert summary["pending"] == 0


@pytest.mark.asyncio
async def test_unacked_message_is_reclaimed_on_next_consume(redis_env, monkeypatch):
    r, tenant, group, stream_key = redis_env
    # Make stranded messages reclaimable immediately instead of after 60s.
    monkeypatch.setattr(redis_stream, "RECLAIM_MIN_IDLE_MS", 0)

    await publish_crash_event(tenant, _payload("first"))

    first = await consume_crash_events(tenant, consumer_group=group)
    assert [e["container_name"] for e in first] == ["first"]
    # Deliberately do NOT ack — simulates a worker crash mid-processing.

    # Next cycle reads no new messages but reclaims the stranded pending one.
    second = await consume_crash_events(tenant, consumer_group=group)
    assert [e["id"] for e in second] == [first[0]["id"]]

    # Now ack and confirm it's gone.
    await ack_crash_event(tenant, second[0]["id"], group)
    summary = await r.xpending(stream_key, group)
    assert summary["pending"] == 0
