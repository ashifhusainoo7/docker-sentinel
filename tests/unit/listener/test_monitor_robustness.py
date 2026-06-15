import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import docker.errors
import pytest

from src.listener.docker_monitor import DockerMonitor


def _sample_event(container_name="web-1", container_id="abc123", action="die"):
    return {
        "Action": action,
        "id": container_id,
        "time": 1714060800,
        "Actor": {
            "ID": container_id,
            "Attributes": {"name": container_name, "image": "nginx:latest", "exitCode": "137"},
        },
    }


@pytest.fixture
def monitor(host_id, tenant_id, fake_db_session_factory):
    return DockerMonitor(
        host_id=host_id,
        tenant_id=tenant_id,
        host_url="tcp://test:2376",
        tls_config=None,
        monitor_all_containers=True,
        container_filter=[],
        db_session_factory=fake_db_session_factory,
    )


@pytest.mark.asyncio
async def test_enqueue_nowait_enqueues_when_space(monitor):
    monitor._queue = asyncio.Queue(maxsize=2)
    monitor._enqueue_nowait({"a": 1})
    assert monitor._queue.qsize() == 1


@pytest.mark.asyncio
async def test_enqueue_nowait_drops_event_when_full(monitor, caplog):
    monitor._queue = asyncio.Queue(maxsize=1)
    monitor._queue.put_nowait({"first": True})
    # Must not raise or block — full queue drops the event with a warning.
    monitor._enqueue_nowait({"second": True})
    assert monitor._queue.qsize() == 1
    assert "queue full" in caplog.text.lower()


@pytest.mark.asyncio
async def test_log_fetch_failure_does_not_drop_event(monitor):
    """A stale/broken docker client must lose only the logs, not the whole event."""
    with patch("src.listener.docker_monitor.publish_crash_event", new=AsyncMock()) as pub:
        client = MagicMock()
        client.containers.get.side_effect = docker.errors.APIError("daemon unreachable")
        await monitor._process_event(_sample_event(), client)

        pub.assert_awaited_once()
        _tenant, payload = pub.await_args.args
        assert payload["logs"] is None
        assert payload["container_name"] == "web-1"


@pytest.mark.asyncio
async def test_set_status_skips_repeated_reconnecting_writes(monitor):
    monitor._loop = asyncio.get_running_loop()
    with patch("src.listener.docker_monitor.update_host_status", new=AsyncMock()) as upd:
        monitor._set_status("reconnecting", "boom 1")  # status changed -> writes
        monitor._set_status("reconnecting", "boom 2")  # unchanged -> skipped
        await asyncio.sleep(0.05)  # let the scheduled coroutine run
    assert upd.call_count == 1


@pytest.mark.asyncio
async def test_set_status_writes_when_status_changes(monitor):
    monitor._loop = asyncio.get_running_loop()
    with patch("src.listener.docker_monitor.update_host_status", new=AsyncMock()) as upd:
        monitor._set_status("connected", None)
        monitor._set_status("reconnecting", "lost")
        await asyncio.sleep(0.05)
    assert upd.call_count == 2
