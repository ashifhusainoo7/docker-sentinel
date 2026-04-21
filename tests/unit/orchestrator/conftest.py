import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def tenant_id():
    return uuid.UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture
def host_id():
    return uuid.UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture
def crash_event_id():
    return uuid.UUID("66666666-6666-6666-6666-666666666666")


@pytest.fixture
def crash_event_payload(host_id):
    return {
        "docker_host_id": str(host_id),
        "container_name": "web-1",
        "container_id": "abc123def456",
        "image": "nginx:latest",
        "exit_code": 137,
        "logs": "out of memory",
        "event_type": "die",
        "event_timestamp": "2026-04-21T12:00:00+00:00",
    }


@pytest.fixture
def initial_state(tenant_id, host_id, crash_event_id, crash_event_payload):
    return {
        "tenant_id": str(tenant_id),
        "crash_event_id": str(crash_event_id),
        "docker_host_id": str(host_id),
        "crash_event": crash_event_payload,
        "analysis": None,
        "cache_hit": False,
        "restart_attempted": False,
        "restart_success": None,
        "slack_sent": False,
        "email_sent": False,
        "call_triggered": False,
        "recent_crash_count": 0,
    }


@pytest.fixture
def fake_session_factory():
    """Factory that yields a mock async session supporting add/execute/commit/get."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return MagicMock(return_value=session)
