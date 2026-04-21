import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listener.docker_monitor import DockerMonitor


def _sample_event(container_name="web-1", container_id="abc123", action="die"):
    return {
        "Action": action,
        "id": container_id,
        "time": 1714060800,  # 2024-04-25T00:00:00Z
        "Actor": {
            "ID": container_id,
            "Attributes": {
                "name": container_name,
                "image": "nginx:latest",
                "exitCode": "137",
            },
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
async def test_process_event_publishes_to_redis(monitor):
    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        fake_client = MagicMock()
        fake_container = MagicMock()
        fake_container.logs.return_value = b"log line 1\nlog line 2"
        fake_client.containers.get.return_value = fake_container

        await monitor._process_event(_sample_event(), fake_client)

        pub.assert_awaited_once()
        tenant_arg, payload = pub.await_args.args
        assert tenant_arg == str(monitor.tenant_id)
        assert payload["container_name"] == "web-1"
        assert payload["container_id"] == "abc123"
        assert payload["exit_code"] == 137
        assert payload["logs"] == "log line 1\nlog line 2"
        assert payload["event_type"] == "die"


@pytest.mark.asyncio
async def test_process_event_skips_filtered_containers(
    host_id, tenant_id, fake_db_session_factory
):
    m = DockerMonitor(
        host_id=host_id,
        tenant_id=tenant_id,
        host_url="tcp://test:2376",
        tls_config=None,
        monitor_all_containers=False,
        container_filter=["api"],
        db_session_factory=fake_db_session_factory,
    )
    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        await m._process_event(_sample_event(container_name="web-1"), MagicMock())
        pub.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_skips_duplicates(monitor):
    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        fake_client = MagicMock()
        fake_client.containers.get.return_value.logs.return_value = b"x"
        await monitor._process_event(_sample_event(), fake_client)
        await monitor._process_event(_sample_event(), fake_client)
        assert pub.await_count == 1


@pytest.mark.asyncio
async def test_process_event_handles_missing_logs(monitor):
    import docker.errors

    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        fake_client = MagicMock()
        fake_client.containers.get.side_effect = docker.errors.NotFound("gone")
        await monitor._process_event(_sample_event(), fake_client)
        assert pub.await_args.args[1]["logs"] is None
