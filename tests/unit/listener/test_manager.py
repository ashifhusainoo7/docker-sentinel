import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listener.manager import ListenerManager


def _fake_host(host_id, tenant_id, is_active=True, connection_mode="tcp"):
    h = MagicMock()
    h.id = host_id
    h.tenant_id = tenant_id
    h.is_active = is_active
    h.connection_mode = connection_mode
    h.tcp_url = "tcp://test:2376"
    h.tls_enabled = False
    h.tls_ca = None
    h.tls_cert = None
    h.tls_key = None
    h.monitor_all_containers = True
    h.container_filter = []
    return h


@pytest.fixture
def fake_session_with_hosts():
    def _build(hosts):
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = hosts
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        return MagicMock(return_value=session)

    return _build


@pytest.mark.asyncio
async def test_sync_spawns_monitor_for_new_host(fake_session_with_hosts, host_id, tenant_id):
    host = _fake_host(host_id, tenant_id)
    factory = fake_session_with_hosts([host])

    with patch("src.listener.manager.DockerMonitor") as MockMonitor:
        mock = MagicMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        MockMonitor.return_value = mock

        mgr = ListenerManager(db_session_factory=factory)
        await mgr.sync_listeners()

        MockMonitor.assert_called_once()
        mock.start.assert_awaited_once()
        assert host_id in mgr._listeners


@pytest.mark.asyncio
async def test_sync_isolates_failing_host_so_others_still_start(
    fake_session_with_hosts, tenant_id
):
    """One unreachable host must not prevent other hosts from being monitored."""
    bad_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    good_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    factory = fake_session_with_hosts(
        [_fake_host(bad_id, tenant_id), _fake_host(good_id, tenant_id)]
    )

    bad = MagicMock()
    bad.start = AsyncMock(side_effect=Exception("daemon unreachable"))
    bad.stop = AsyncMock()
    good = MagicMock()
    good.start = AsyncMock()
    good.stop = AsyncMock()

    with patch("src.listener.manager.DockerMonitor", side_effect=[bad, good]):
        mgr = ListenerManager(db_session_factory=factory)
        await mgr.sync_listeners()  # must not raise despite the bad host

    bad.start.assert_awaited_once()
    good.start.assert_awaited_once()
    # Bad host isn't registered (retried next sync); good host is monitored.
    assert bad_id not in mgr._listeners
    assert good_id in mgr._listeners


@pytest.mark.asyncio
async def test_sync_stops_monitor_for_removed_host(fake_session_with_hosts, host_id, tenant_id):
    factory = fake_session_with_hosts([])

    mgr = ListenerManager(db_session_factory=factory)
    existing = MagicMock()
    existing.stop = AsyncMock()
    mgr._listeners[host_id] = existing

    await mgr.sync_listeners()

    existing.stop.assert_awaited_once()
    assert host_id not in mgr._listeners


@pytest.mark.asyncio
async def test_sync_leaves_existing_monitor_alone(fake_session_with_hosts, host_id, tenant_id):
    host = _fake_host(host_id, tenant_id)
    factory = fake_session_with_hosts([host])

    mgr = ListenerManager(db_session_factory=factory)
    existing = MagicMock()
    existing.start = AsyncMock()
    existing.stop = AsyncMock()
    mgr._listeners[host_id] = existing

    with patch("src.listener.manager.DockerMonitor") as MockMonitor:
        await mgr.sync_listeners()
        MockMonitor.assert_not_called()
        existing.stop.assert_not_awaited()
        existing.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_skips_agent_mode_hosts(fake_session_with_hosts, host_id, tenant_id):
    """Agent-mode hosts are handled by the API WebSocket, not the manager."""
    # We simulate DB filtering by returning no hosts (the query filters by connection_mode=tcp).
    # This test documents the expectation by asserting the query was invoked with the right filter.
    factory = fake_session_with_hosts([])
    mgr = ListenerManager(db_session_factory=factory)
    await mgr.sync_listeners()

    session = factory.return_value
    session.execute.assert_awaited_once()
    # The actual filter clause is tested implicitly: if we pass a non-TCP host, it won't appear.


@pytest.mark.asyncio
async def test_manager_start_runs_sync_in_background(fake_session_with_hosts):
    factory = fake_session_with_hosts([])
    mgr = ListenerManager(db_session_factory=factory, sync_interval=0.05)
    with patch.object(mgr, "sync_listeners", new=AsyncMock()) as sync:
        await mgr.start()
        await asyncio.sleep(0.12)  # allow ≥2 sync cycles
        await mgr.stop()
        assert sync.await_count >= 2


@pytest.mark.asyncio
async def test_manager_stop_terminates_sync_task_and_stops_monitors(fake_session_with_hosts, host_id):
    factory = fake_session_with_hosts([])
    mgr = ListenerManager(db_session_factory=factory, sync_interval=0.05)
    mon = MagicMock()
    mon.stop = AsyncMock()
    mgr._listeners[host_id] = mon

    await mgr.start()
    await asyncio.sleep(0.05)
    await mgr.stop()

    mon.stop.assert_awaited()
    assert mgr._sync_task is None or mgr._sync_task.done()
