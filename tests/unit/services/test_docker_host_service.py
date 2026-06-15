import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from docker.errors import DockerException
from fastapi import HTTPException

from src.services import docker_host_service


def _host(connection_mode: str = "tcp", tcp_url: str | None = "tcp://1.2.3.4:2375") -> MagicMock:
    host = MagicMock()
    host.connection_mode = connection_mode
    host.tcp_url = tcp_url
    return host


@pytest.mark.asyncio
async def test_raises_404_when_host_missing():
    with patch.object(docker_host_service, "get_host", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await docker_host_service.test_host_connection(
                MagicMock(), uuid.uuid4(), uuid.uuid4()
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_agent_mode_is_not_probed():
    host = _host(connection_mode="agent")
    with patch.object(docker_host_service, "get_host", AsyncMock(return_value=host)):
        result = await docker_host_service.test_host_connection(
            MagicMock(), uuid.uuid4(), uuid.uuid4()
        )
    assert result["ok"] is False
    assert result["mode"] == "agent"
    assert "message" in result


@pytest.mark.asyncio
async def test_tcp_mode_missing_url():
    host = _host(connection_mode="tcp", tcp_url=None)
    with patch.object(docker_host_service, "get_host", AsyncMock(return_value=host)):
        result = await docker_host_service.test_host_connection(
            MagicMock(), uuid.uuid4(), uuid.uuid4()
        )
    assert result == {"ok": False, "mode": "tcp", "message": "No tcp_url configured"}


@pytest.mark.asyncio
async def test_tcp_probe_success_returns_version_and_count():
    host = _host()
    fake_client = MagicMock()
    fake_client.version.return_value = {"Version": "24.0.7", "ApiVersion": "1.43"}
    fake_client.containers.list.return_value = [MagicMock(), MagicMock(), MagicMock()]

    with (
        patch.object(docker_host_service, "get_host", AsyncMock(return_value=host)),
        patch.object(docker_host_service.docker, "DockerClient", return_value=fake_client) as ctor,
    ):
        result = await docker_host_service.test_host_connection(
            MagicMock(), uuid.uuid4(), uuid.uuid4()
        )

    assert result["ok"] is True
    assert result["mode"] == "tcp"
    assert result["docker_version"] == "24.0.7"
    assert result["api_version"] == "1.43"
    assert result["running_containers"] == 3
    assert isinstance(result["latency_ms"], int)
    # Probed the configured tcp_url with a bounded timeout.
    assert ctor.call_args.kwargs.get("base_url") == host.tcp_url
    assert ctor.call_args.kwargs.get("timeout") == 5
    # Client is always closed on success.
    fake_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_tcp_probe_docker_exception_is_caught():
    host = _host()
    with (
        patch.object(docker_host_service, "get_host", AsyncMock(return_value=host)),
        patch.object(
            docker_host_service.docker,
            "DockerClient",
            side_effect=DockerException("cannot connect to daemon"),
        ),
    ):
        result = await docker_host_service.test_host_connection(
            MagicMock(), uuid.uuid4(), uuid.uuid4()
        )
    assert result["ok"] is False
    assert result["mode"] == "tcp"
    assert "cannot connect to daemon" in result["message"]


@pytest.mark.asyncio
async def test_tcp_probe_generic_exception_includes_type_name():
    host = _host()
    with (
        patch.object(docker_host_service, "get_host", AsyncMock(return_value=host)),
        patch.object(
            docker_host_service.docker, "DockerClient", side_effect=ValueError("boom")
        ),
    ):
        result = await docker_host_service.test_host_connection(
            MagicMock(), uuid.uuid4(), uuid.uuid4()
        )
    assert result["ok"] is False
    assert "ValueError" in result["message"]
    assert "boom" in result["message"]


@pytest.mark.asyncio
async def test_client_is_closed_even_when_probe_fails_midway():
    """If version() raises after the client is created, the finally block must close it."""
    host = _host()
    fake_client = MagicMock()
    fake_client.version.side_effect = DockerException("api error")

    with (
        patch.object(docker_host_service, "get_host", AsyncMock(return_value=host)),
        patch.object(docker_host_service.docker, "DockerClient", return_value=fake_client),
    ):
        result = await docker_host_service.test_host_connection(
            MagicMock(), uuid.uuid4(), uuid.uuid4()
        )

    assert result["ok"] is False
    fake_client.close.assert_called_once()
