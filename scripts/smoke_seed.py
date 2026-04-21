"""One-shot seed for the Phase 1 smoke test.

Creates a tenant + DockerHost pointing to the local Docker Desktop named pipe
(Windows) so the worker's DockerMonitor can attach. Prints the tenant_id so
the caller can tail the corresponding Redis stream.
"""

import asyncio
import os
import uuid

from sqlalchemy import select

from src.models.docker_host import DockerHost
from src.models.tenant import Tenant
from src.services.database import async_session_factory


async def seed() -> None:
    npipe_url = os.environ.get(
        "SMOKE_DOCKER_URL", "npipe:////./pipe/docker_engine"
    )
    async with async_session_factory() as s:
        existing = (
            await s.execute(select(Tenant).where(Tenant.name == "smoke-test"))
        ).scalar_one_or_none()
        if existing is not None:
            await s.execute(
                DockerHost.__table__.delete().where(
                    DockerHost.tenant_id == existing.id
                )
            )
            await s.delete(existing)
            await s.commit()

        tenant = Tenant(id=uuid.uuid4(), name="smoke-test", slug="smoke-test")
        s.add(tenant)
        await s.flush()
        host = DockerHost(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="local-docker",
            connection_mode="tcp",
            tcp_url=npipe_url,
            is_active=True,
            monitor_all_containers=True,
            container_filter=[],
        )
        s.add(host)
        await s.commit()
        print(f"TENANT_ID={tenant.id}")
        print(f"HOST_ID={host.id}")


if __name__ == "__main__":
    asyncio.run(seed())
