import json

import redis.asyncio as redis

from config.settings import settings

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def publish_crash_event(tenant_id: str, event_data: dict) -> str:
    """Publish a crash event to the tenant's Redis stream."""
    r = await get_redis()
    stream_key = f"crashes:{tenant_id}"
    message_id = await r.xadd(stream_key, {"data": json.dumps(event_data)})
    return message_id


async def consume_crash_events(
    tenant_id: str, consumer_group: str = "orchestrator", consumer_name: str = "worker-1"
) -> list[dict]:
    """Consume crash events from the tenant's Redis stream."""
    r = await get_redis()
    stream_key = f"crashes:{tenant_id}"

    # Create consumer group if it doesn't exist
    try:
        await r.xgroup_create(stream_key, consumer_group, id="0", mkstream=True)
    except redis.ResponseError:
        pass  # Group already exists

    messages = await r.xreadgroup(
        consumer_group, consumer_name, {stream_key: ">"}, count=10, block=5000
    )

    events = []
    for stream, msgs in messages:
        for msg_id, data in msgs:
            events.append({"id": msg_id, **json.loads(data["data"])})
            await r.xack(stream_key, consumer_group, msg_id)
    return events


async def publish_agent_event(tenant_id: str, event_data: dict) -> None:
    """Publish an event from an agent connection to the processing channel."""
    r = await get_redis()
    channel = f"agent:events:{tenant_id}"
    await r.publish(channel, json.dumps(event_data))
