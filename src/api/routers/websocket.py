import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.api.deps import get_db

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("sentinel.websocket")


@router.websocket("/api/v1/ws/agent")
async def agent_websocket(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for agent containers.

    Agents authenticate with API key, then stream Docker events.
    Events are published to Redis for the worker to consume.
    """
    async with (await get_db().__anext__()) if False else _Placeholder():
        pass

    # Placeholder — full implementation will:
    # 1. Validate API key from query param
    # 2. Accept WebSocket connection
    # 3. Receive Docker events as JSON messages
    # 4. Publish each event to Redis stream for the tenant
    # 5. Handle disconnection gracefully

    await websocket.accept()
    try:
        # Validate API key
        # api_key = await api_key_service.validate_api_key(db, token)
        # if not api_key:
        #     await websocket.close(code=4001, reason="Invalid API key")
        #     return

        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            logger.info("Agent event received: %s", event.get("container_name", "unknown"))
            # await redis_stream.publish_agent_event(str(api_key.tenant_id), event)
    except WebSocketDisconnect:
        logger.info("Agent disconnected")


@router.websocket("/api/v1/ws/live")
async def live_feed(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for live crash feed in dashboard.

    Authenticated users receive real-time crash events for their tenant.
    """
    await websocket.accept()
    try:
        # Placeholder — full implementation will:
        # 1. Validate JWT from query param
        # 2. Subscribe to tenant's Redis pub/sub channel
        # 3. Forward crash events to WebSocket
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        logger.info("Live feed client disconnected")


class _Placeholder:
    """Placeholder context manager."""
    async def __aenter__(self): return None
    async def __aexit__(self, *args): pass
