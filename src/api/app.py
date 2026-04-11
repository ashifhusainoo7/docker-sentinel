from fastapi import FastAPI

from src.api.middleware import setup_middleware
from src.api.routers import register_routers


def create_app() -> FastAPI:
    app = FastAPI(
        title="DockerSentinel API",
        description="Multi-Agent Docker Container Crash Monitor — SaaS Platform",
        version="0.1.0",
    )

    setup_middleware(app)
    register_routers(app)

    return app
