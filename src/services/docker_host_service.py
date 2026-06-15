import asyncio
import time
import uuid

import docker
from docker.errors import DockerException
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.docker_host import DockerHost
from src.schemas.docker_host import DockerHostCreate, DockerHostUpdate


async def create_host(
    db: AsyncSession, tenant_id: uuid.UUID, data: DockerHostCreate
) -> DockerHost:
    host = DockerHost(
        tenant_id=tenant_id,
        name=data.name,
        connection_mode=data.connection_mode,
        tcp_url=data.tcp_url,
        tls_enabled=data.tls_enabled,
        monitor_all_containers=data.monitor_all_containers,
        container_filter=data.container_filter,
    )
    if data.connection_mode == "agent":
        host.agent_id = uuid.uuid4().hex
    db.add(host)
    await db.flush()
    return host


async def list_hosts(db: AsyncSession, tenant_id: uuid.UUID) -> list[DockerHost]:
    result = await db.execute(
        select(DockerHost).where(DockerHost.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def get_host(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID
) -> DockerHost | None:
    result = await db.execute(
        select(DockerHost).where(
            DockerHost.id == host_id, DockerHost.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def update_host(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID, data: DockerHostUpdate
) -> DockerHost | None:
    host = await get_host(db, tenant_id, host_id)
    if not host:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(host, field, value)
    await db.flush()
    return host


async def delete_host(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID
) -> bool:
    host = await get_host(db, tenant_id, host_id)
    if not host:
        return False
    await db.delete(host)
    await db.flush()
    return True


async def test_host_connection(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID
) -> dict:
    """Probe the Docker daemon for this host and return version + container count.

    TCP hosts: open a fresh ``docker.DockerClient`` against ``tcp_url`` with a
    short timeout. Agent hosts: cannot be probed from the API server, so
    return a structured 'not-supported' response instead of erroring.
    """
    host = await get_host(db, tenant_id, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    if host.connection_mode == "agent":
        return {
            "ok": False,
            "mode": "agent",
            "message": "Agent-based hosts don't support server-side connection tests.",
        }

    if not host.tcp_url:
        return {"ok": False, "mode": "tcp", "message": "No tcp_url configured"}

    def _probe() -> dict:
        started = time.perf_counter()
        client = docker.DockerClient(base_url=host.tcp_url, timeout=5)
        try:
            version = client.version()
            containers = client.containers.list(all=False)
            return {
                "ok": True,
                "mode": "tcp",
                "docker_version": version.get("Version"),
                "api_version": version.get("ApiVersion"),
                "running_containers": len(containers),
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        finally:
            client.close()

    try:
        result = await asyncio.to_thread(_probe)
    except DockerException as e:
        return {"ok": False, "mode": "tcp", "message": str(e)[:200]}
    except Exception as e:
        return {"ok": False, "mode": "tcp", "message": f"{type(e).__name__}: {str(e)[:200]}"}

    return result
