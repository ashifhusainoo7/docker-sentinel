import asyncio
import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select

from src.models.crash_event import CrashEvent
from src.models.tenant import Tenant
from src.orchestrator.graph import crash_workflow
from src.services.database import async_session_factory

logger = logging.getLogger("sentinel.worker")

ConsumerFn = Callable[[uuid.UUID, asyncio.Event], Awaitable[None]]


class TenantConsumerSupervisor:
    """Maintains one asyncio consumer task per tenant.

    Polls the tenants table every sync_interval seconds; spawns consumers
    for new tenants and cancels consumers for removed tenants.
    """

    def __init__(
        self,
        db_session_factory,
        consume_fn: ConsumerFn,
        sync_interval: float = 30.0,
    ):
        self._db_session_factory = db_session_factory
        self._consume_fn = consume_fn
        self._sync_interval = sync_interval
        self._tasks: dict[uuid.UUID, asyncio.Task] = {}
        self._shutdown = asyncio.Event()
        self._sync_task: asyncio.Task | None = None

    async def sync_tenants(self) -> None:
        async with self._db_session_factory() as session:
            result = await session.execute(select(Tenant))
            tenants = list(result.scalars().all())
        desired = {t.id for t in tenants}

        for tid in list(self._tasks.keys()):
            if tid not in desired:
                task = self._tasks.pop(tid)
                task.cancel()

        for tid in desired:
            if tid in self._tasks:
                continue
            self._tasks[tid] = asyncio.create_task(
                self._consume_fn(tid, self._shutdown), name=f"consume-{tid}"
            )

    async def start(self) -> None:
        if self._sync_task is not None:
            return
        self._shutdown.clear()
        self._sync_task = asyncio.create_task(self._loop(), name="tenant-sync")

    async def stop(self) -> None:
        self._shutdown.set()
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except (asyncio.CancelledError, Exception):
                pass
            self._sync_task = None
        if self._tasks:
            for t in self._tasks.values():
                t.cancel()
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
            self._tasks.clear()

    async def _loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                await self.sync_tenants()
            except Exception:
                logger.exception("Tenant sync failure")
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(), timeout=self._sync_interval
                )
            except asyncio.TimeoutError:
                pass


async def _process_event(
    event: dict, tenant_id: uuid.UUID, db_session_factory
) -> None:
    """Insert a pending CrashEvent row, then invoke the LangGraph workflow."""
    crash_row = CrashEvent(
        tenant_id=tenant_id,
        docker_host_id=uuid.UUID(event["docker_host_id"]),
        container_name=event.get("container_name", ""),
        container_id=event.get("container_id", ""),
        image=event.get("image", ""),
        exit_code=event.get("exit_code"),
        logs=event.get("logs"),
    )
    async with db_session_factory() as session:
        session.add(crash_row)
        await session.flush()
        crash_event_id = crash_row.id
        await session.commit()

    state = {
        "crash_event_id": str(crash_event_id),
        "tenant_id": str(tenant_id),
        "event_data": event,
    }
    try:
        await crash_workflow.ainvoke(state)
    except NotImplementedError:
        logger.info(
            "LangGraph node not implemented yet (expected during Phase 1) for event=%s",
            event.get("id"),
        )
    except Exception:
        logger.exception(
            "Error invoking crash workflow for event=%s", event.get("id")
        )


async def _consume_tenant(
    tenant_id: uuid.UUID, shutdown: asyncio.Event
) -> None:
    """Loop: consume from crashes:{tenant_id}, process, repeat until shutdown."""
    from src.services.redis_stream import consume_crash_events

    while not shutdown.is_set():
        try:
            events = await consume_crash_events(
                str(tenant_id),
                consumer_group="orchestrator",
                consumer_name="worker-1",
            )
            for event in events:
                if shutdown.is_set():
                    break
                await _process_event(event, tenant_id, async_session_factory)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Consumer error for tenant=%s; retrying in 5s", tenant_id
            )
            try:
                await asyncio.wait_for(shutdown.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    import signal

    from src.listener.manager import ListenerManager

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting DockerSentinel worker")

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_shutdown(signame: str) -> None:
        logger.info("Received %s, shutting down", signame)
        shutdown_event.set()

    for signame in ("SIGTERM", "SIGINT"):
        try:
            loop.add_signal_handler(
                getattr(signal, signame), _request_shutdown, signame
            )
        except (NotImplementedError, RuntimeError):
            # Windows doesn't support add_signal_handler for SIGTERM.
            signal.signal(
                getattr(signal, signame),
                lambda *_args, n=signame: _request_shutdown(n),
            )

    manager = ListenerManager(db_session_factory=async_session_factory)
    supervisor = TenantConsumerSupervisor(
        db_session_factory=async_session_factory,
        consume_fn=_consume_tenant,
    )

    await manager.start()
    await supervisor.start()

    await shutdown_event.wait()

    logger.info("Shutdown requested; stopping supervisor and manager")
    await asyncio.wait_for(supervisor.stop(), timeout=10.0)
    await asyncio.wait_for(manager.stop(), timeout=10.0)
    logger.info("Worker stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
