import json
from unittest.mock import AsyncMock, patch

import pytest

from src.services import redis_stream


class FakeRedis:
    """Minimal async Redis stand-in recording acks and returning canned reads."""

    def __init__(self, new_msgs=None, reclaim=None):
        self._new = new_msgs or []
        self._reclaim = reclaim or []
        self.acked: list[str] = []
        self.read_with_name: str | None = None
        self.closed = False

    async def xgroup_create(self, *a, **k):
        return True

    async def xautoclaim(self, stream, group, name, min_idle_time, start_id, count):
        return ("0-0", self._reclaim, [])

    async def xreadgroup(self, group, name, streams, count, block):
        self.read_with_name = name
        return [("crashes:t", self._new)] if self._new else []

    async def xack(self, stream, group, msg_id):
        self.acked.append(msg_id)

    async def aclose(self):
        self.closed = True


def _msg(msg_id, **payload):
    return (msg_id, {"data": json.dumps(payload)})


@pytest.mark.asyncio
async def test_consume_does_not_ack_on_read():
    fake = FakeRedis(new_msgs=[_msg("1-0", container_name="web", docker_host_id="h")])
    with patch.object(redis_stream, "get_redis", AsyncMock(return_value=fake)):
        events = await redis_stream.consume_crash_events("t")
    assert [e["id"] for e in events] == ["1-0"]
    assert events[0]["container_name"] == "web"
    # Critical: reading must NOT acknowledge — ack happens only after processing.
    assert fake.acked == []


@pytest.mark.asyncio
async def test_consume_includes_reclaimed_pending_messages():
    fake = FakeRedis(
        new_msgs=[_msg("2-0", container_name="new")],
        reclaim=[_msg("9-0", container_name="stranded")],
    )
    with patch.object(redis_stream, "get_redis", AsyncMock(return_value=fake)):
        events = await redis_stream.consume_crash_events("t")
    ids = {e["id"] for e in events}
    assert ids == {"9-0", "2-0"}  # reclaimed pending + newly delivered


@pytest.mark.asyncio
async def test_consume_uses_unique_per_process_consumer_name():
    fake = FakeRedis(new_msgs=[_msg("1-0")])
    with patch.object(redis_stream, "get_redis", AsyncMock(return_value=fake)):
        await redis_stream.consume_crash_events("t")
    assert fake.read_with_name == redis_stream.CONSUMER_NAME
    assert redis_stream.CONSUMER_NAME != "worker-1"  # no shared hardcoded identity


@pytest.mark.asyncio
async def test_ack_crash_event_acks_single_message():
    fake = FakeRedis()
    with patch.object(redis_stream, "get_redis", AsyncMock(return_value=fake)):
        await redis_stream.ack_crash_event("t", "5-0", "orchestrator")
    assert fake.acked == ["5-0"]


@pytest.mark.asyncio
async def test_reset_redis_closes_and_clears_singleton():
    fake = FakeRedis()
    redis_stream._redis_client = fake
    await redis_stream.reset_redis()
    assert fake.closed is True
    assert redis_stream._redis_client is None
