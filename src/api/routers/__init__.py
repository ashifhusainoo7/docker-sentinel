from fastapi import FastAPI

from src.api.routers import (
    api_keys,
    auth,
    crash_events,
    dashboard,
    docker_hosts,
    escalations,
    health,
    notifications,
    tenants,
    websocket,
)


def register_routers(app: FastAPI) -> None:
    # Health + metrics (no auth)
    app.include_router(health.router)

    # Auth routes
    app.include_router(auth.router)

    # Authenticated API routes
    app.include_router(tenants.router)
    app.include_router(docker_hosts.router)
    app.include_router(crash_events.router)
    app.include_router(api_keys.router)
    app.include_router(notifications.router)
    app.include_router(escalations.router)
    app.include_router(dashboard.router)

    # WebSocket routes
    app.include_router(websocket.router)
