import asyncio
import logging
import uuid

import docker
from sqlalchemy import select

from src.listener.docker_monitor import DockerMonitor
from src.models.docker_host import DockerHost

logger = logging.getLogger("sentinel.listener.manager")


class ListenerManager:
    """Owns the lifecycle of DockerMonitor instances across all tenants.

    Polls PostgreSQL every sync_interval seconds. Spawns/stops monitors
    as docker_hosts rows appear/disappear or are toggled (de)active.
    """

    def __init__(self, db_session_factory, sync_interval: float = 30.0):
        self._db_session_factory = db_session_factory
        self._sync_interval = sync_interval
        self._listeners: dict[uuid.UUID, DockerMonitor] = {}
        self._sync_task: asyncio.Task | None = None
        self._shutdown = asyncio.Event()

    async def sync_listeners(self) -> None:
        async with self._db_session_factory() as session:
            result = await session.execute(
                select(DockerHost).where(
                    DockerHost.is_active == True,  # noqa: E712
                    DockerHost.connection_mode == "tcp",
                )
            )
            hosts = list(result.scalars().all())

        desired: dict[uuid.UUID, DockerHost] = {h.id: h for h in hosts}

        # Stop monitors whose hosts are gone or deactivated.
        for host_id in list(self._listeners.keys()):
            if host_id not in desired:
                logger.info("Stopping listener for removed host %s", host_id)
                try:
                    await self._listeners[host_id].stop()
                finally:
                    self._listeners.pop(host_id, None)

        # Spawn monitors for new hosts.
        for host_id, host in desired.items():
            if host_id in self._listeners:
                continue
            logger.info("Spawning listener for host %s", host_id)
            tls_config = self._build_tls_config(host)
            monitor = DockerMonitor(
                host_id=host.id,
                tenant_id=host.tenant_id,
                host_url=host.tcp_url,
                tls_config=tls_config,
                monitor_all_containers=host.monitor_all_containers,
                container_filter=host.container_filter or [],
                db_session_factory=self._db_session_factory,
            )
            await monitor.start()
            self._listeners[host_id] = monitor

    def _build_tls_config(self, host: DockerHost):
        if not host.tls_enabled:
            return None
        # Minimal TLSConfig from PEM-encoded strings stored in DB.
        # For portfolio-scale, we trust the certs from DB. A production build
        # would write these to tempfiles with tight permissions.
        import tempfile

        def _write(pem: str) -> str:
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", mode="w")
            f.write(pem)
            f.close()
            return f.name

        return docker.tls.TLSConfig(
            ca_cert=_write(host.tls_ca) if host.tls_ca else None,
            client_cert=(
                (_write(host.tls_cert), _write(host.tls_key))
                if host.tls_cert and host.tls_key
                else None
            ),
            verify=True,
        )

    async def start(self) -> None:
        raise NotImplementedError("Implemented in Task 9")

    async def stop(self) -> None:
        raise NotImplementedError("Implemented in Task 9")
