import logging
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.docker_host import DockerHost

logger = logging.getLogger("sentinel.listener.status")


async def update_host_status(
    session_factory: async_sessionmaker,
    host_id: uuid.UUID,
    status: str,
    message: str | None,
) -> None:
    """Best-effort update of docker_hosts.status. Never raises."""
    try:
        async with session_factory() as session:
            await session.execute(
                update(DockerHost)
                .where(DockerHost.id == host_id)
                .values(status=status, status_message=message)
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to update status for host %s", host_id)
