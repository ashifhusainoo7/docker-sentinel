import asyncio
import logging
import uuid

from sqlalchemy import select

from src.listener._tls import build_tls_config
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

        # Spawn monitors for new hosts. One unreachable host must not prevent the
        # others from being monitored, so each start is isolated — a failure is
        # logged and retried on the next sync rather than aborting the loop.
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
            try:
                await monitor.start()
            except Exception:
                logger.exception(
                    "Failed to start listener for host %s; will retry next sync",
                    host_id,
                )
                continue
            self._listeners[host_id] = monitor

    def _build_tls_config(self, host: DockerHost):
        return build_tls_config(host)

    async def start(self) -> None:
        if self._sync_task is not None:
            return
        self._shutdown.clear()
        self._sync_task = asyncio.create_task(self._sync_loop(), name="listener-sync")
        logger.info("ListenerManager started (interval=%.1fs)", self._sync_interval)

    async def stop(self) -> None:
        self._shutdown.set()
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except (asyncio.CancelledError, Exception):
                pass
            self._sync_task = None
        # Stop all monitors in parallel.
        if self._listeners:
            await asyncio.gather(
                *(m.stop() for m in self._listeners.values()),
                return_exceptions=True,
            )
            self._listeners.clear()
        logger.info("ListenerManager stopped")

    async def _sync_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                await self.sync_listeners()
            except Exception:
                logger.exception("ListenerManager sync failure")
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(), timeout=self._sync_interval
                )
            except TimeoutError:
                pass  # normal path — interval elapsed
