import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.worker.main import TenantConsumerSupervisor


def _fake_tenant(tid):
    t = MagicMock()
    t.id = tid
    return t


@pytest.fixture
def factory_with_tenants():
    def _build(tenants):
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = tenants
        session.execute = AsyncMock(return_value=result)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        return MagicMock(return_value=session)

    return _build


@pytest.mark.asyncio
async def test_supervisor_spawns_task_per_tenant(factory_with_tenants):
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    factory = factory_with_tenants([_fake_tenant(t1), _fake_tenant(t2)])
    consume = AsyncMock()
    sup = TenantConsumerSupervisor(
        db_session_factory=factory, consume_fn=consume, sync_interval=0.05
    )
    await sup.sync_tenants()
    assert t1 in sup._tasks
    assert t2 in sup._tasks
    await sup.stop()


@pytest.mark.asyncio
async def test_supervisor_cancels_task_for_removed_tenant(factory_with_tenants):
    t1 = uuid.uuid4()
    factory = factory_with_tenants([])

    async def never_ending(tid, shutdown):
        await shutdown.wait()

    sup = TenantConsumerSupervisor(
        db_session_factory=factory, consume_fn=never_ending, sync_interval=0.05
    )
    fake_task = asyncio.create_task(asyncio.sleep(10))
    sup._tasks[t1] = fake_task
    await sup.sync_tenants()
    await asyncio.sleep(0.01)
    assert t1 not in sup._tasks
    assert fake_task.cancelled() or fake_task.done()


@pytest.mark.asyncio
async def test_supervisor_start_stop_lifecycle(factory_with_tenants):
    factory = factory_with_tenants([])
    calls = []

    async def consume(tid, shutdown):
        calls.append(tid)
        await shutdown.wait()

    sup = TenantConsumerSupervisor(
        db_session_factory=factory, consume_fn=consume, sync_interval=0.05
    )
    await sup.start()
    await asyncio.sleep(0.12)
    await sup.stop()
    assert sup._sync_task is None or sup._sync_task.done()
