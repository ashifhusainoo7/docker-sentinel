import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import docker.errors
import pytest

from src.orchestrator.nodes import attempt_restart


def _fake_host(host_id, tls_enabled=False):
    h = MagicMock()
    h.id = host_id
    h.connection_mode = "tcp"
    h.tcp_url = "tcp://test:2376"
    h.tls_enabled = tls_enabled
    h.tls_ca = None
    h.tls_cert = None
    h.tls_key = None
    return h


@pytest.mark.asyncio
async def test_attempt_restart_success(initial_state, host_id):
    fake_host = _fake_host(host_id)
    fake_container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client) as client_ctor:
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": True}
    client_ctor.assert_called_once()
    fake_container.restart.assert_called_once_with(timeout=10)
    fake_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_restart_container_not_found(initial_state, host_id):
    fake_host = _fake_host(host_id)
    fake_client = MagicMock()
    fake_client.containers.get.side_effect = docker.errors.NotFound("gone")

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client):
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": False}
    fake_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_restart_host_missing(initial_state):
    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient") as client_ctor:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": False, "restart_success": None}
    client_ctor.assert_not_called()


@pytest.mark.asyncio
async def test_attempt_restart_docker_api_error(initial_state, host_id):
    fake_host = _fake_host(host_id)
    fake_client = MagicMock()
    fake_client.containers.get.side_effect = docker.errors.APIError("daemon down")

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client):
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": False}


@pytest.mark.asyncio
async def test_attempt_restart_agent_mode_host_skipped(initial_state, host_id):
    """Agent-mode hosts have no tcp_url; restart must be skipped cleanly."""
    agent_host = MagicMock()
    agent_host.id = host_id
    agent_host.connection_mode = "agent"
    agent_host.tcp_url = None
    agent_host.tls_enabled = False

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient") as client_ctor:
        session = AsyncMock()
        session.get = AsyncMock(return_value=agent_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": False, "restart_success": None}
    client_ctor.assert_not_called()
