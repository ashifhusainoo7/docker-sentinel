import json
import os
import socket

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError

from config.settings import settings

_redis_client: redis.Redis | None = None

# Stable, unique consumer identity for this worker process. Redis Streams keys
# the Pending Entries List by consumer name within a group, so two worker
# processes must never share a name or they would steal each other's messages.
CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}"

# Reclaim messages that have been delivered but left un-acked longer than this
# (e.g. because a worker crashed mid-processing) so they are retried, not lost.
RECLAIM_MIN_IDLE_MS = 60_000


async def get_redis() -> redis.Redis:
    """Return the shared async Redis client, building it with timeouts + retry.

    The client retries transient connection/timeout errors with exponential
    backoff and runs periodic health checks so a momentary blip doesn't surface
    as a hard failure. Use ``reset_redis()`` to force a rebuild after a fatal
    connection error.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=5,
            health_check_interval=30,
            retry=Retry(ExponentialBackoff(cap=10, base=0.5), retries=3),
            retry_on_error=[RedisConnectionError, RedisTimeoutError],
        )
    return _redis_client


async def reset_redis() -> None:
    """Drop the cached client so the next ``get_redis()`` reconnects.

    Called after a connection error: the singleton would otherwise hand back the
    same broken client forever, so all consumers would fail until restart.
    """
    global _redis_client
    client = _redis_client
    _redis_client = None
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass


async def publish_crash_event(tenant_id: str, event_data: dict) -> str:
    """Publish a crash event to the tenant's Redis stream."""
    r = await get_redis()
    stream_key = f"crashes:{tenant_id}"
    message_id = await r.xadd(stream_key, {"data": json.dumps(event_data)})
    return message_id


async def _ensure_group(r: redis.Redis, stream_key: str, consumer_group: str) -> None:
    try:
        await r.xgroup_create(stream_key, consumer_group, id="0", mkstream=True)
    except ResponseError:
        pass  # Group already exists.


async def consume_crash_events(
    tenant_id: str,
    consumer_group: str = "orchestrator",
    consumer_name: str | None = None,
) -> list[dict]:
    """Read crash events for a tenant **without** acknowledging them.

    The caller MUST ack each event via :func:`ack_crash_event` only after it has
    been processed successfully. Un-acked messages stay in the consumer group's
    pending list and are reclaimed on a later call, so a worker crash (or a DB
    error mid-processing) retries the event instead of silently dropping it.

    Each call first reclaims messages stranded by a previous consumer, then reads
    new messages.
    """
    r = await get_redis()
    name = consumer_name or CONSUMER_NAME
    stream_key = f"crashes:{tenant_id}"

    await _ensure_group(r, stream_key, consumer_group)

    events: list[dict] = []

    # 1. Reclaim messages left pending (read but un-acked) by a crashed/slow
    #    consumer, so they are retried rather than lost.
    try:
        _cursor, claimed, _deleted = await r.xautoclaim(
            stream_key,
            consumer_group,
            name,
            min_idle_time=RECLAIM_MIN_IDLE_MS,
            start_id="0-0",
            count=10,
        )
        for msg_id, data in claimed:
            if data and "data" in data:
                events.append({"id": msg_id, **json.loads(data["data"])})
    except ResponseError:
        pass  # Group/stream not ready yet; new-message read below still runs.

    # 2. Read newly-delivered messages.
    messages = await r.xreadgroup(
        consumer_group, name, {stream_key: ">"}, count=10, block=5000
    )
    for _stream, msgs in messages or []:
        for msg_id, data in msgs:
            events.append({"id": msg_id, **json.loads(data["data"])})

    return events


async def ack_crash_event(
    tenant_id: str, msg_id: str, consumer_group: str = "orchestrator"
) -> None:
    """Acknowledge a single processed message, removing it from the pending list."""
    r = await get_redis()
    await r.xack(f"crashes:{tenant_id}", consumer_group, msg_id)


async def publish_agent_event(tenant_id: str, event_data: dict) -> None:
    """Publish an event from an agent connection to the processing channel."""
    r = await get_redis()
    channel = f"agent:events:{tenant_id}"
    await r.publish(channel, json.dumps(event_data))
