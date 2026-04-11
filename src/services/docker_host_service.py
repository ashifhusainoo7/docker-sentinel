import uuid

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
    """Placeholder — will test Docker daemon connectivity."""
    raise NotImplementedError(
        "Docker host connection test not yet implemented. "
        "Will use Docker SDK to connect to tcp_url and verify access."
    )
