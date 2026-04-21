import asyncio
import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select

from src.models.tenant import Tenant
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


async def main() -> None:
    raise NotImplementedError("Implemented in Task 12")
