import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.worker.main import _process_event


@pytest.fixture
def tenant_id():
    return uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def event_payload():
    return {
        "id": "redis-msg-id-1",
        "docker_host_id": str(uuid.uuid4()),
        "container_name": "web-1",
        "container_id": "abc123",
        "image": "nginx:latest",
        "exit_code": 137,
        "logs": "out of memory",
        "event_type": "die",
        "event_timestamp": "2026-04-21T12:00:00+00:00",
    }


@pytest.fixture
def mock_session_factory():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return MagicMock(return_value=session)


@pytest.mark.asyncio
async def test_process_event_inserts_crash_event_row(
    tenant_id, event_payload, mock_session_factory
):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock()
        await _process_event(event_payload, tenant_id, mock_session_factory)
        session = mock_session_factory.return_value
        session.add.assert_called_once()
        added = session.add.call_args.args[0]
        assert added.tenant_id == tenant_id
        assert added.container_name == "web-1"
        assert added.exit_code == 137


@pytest.mark.asyncio
async def test_process_event_invokes_langgraph_workflow(
    tenant_id, event_payload, mock_session_factory
):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock()
        await _process_event(event_payload, tenant_id, mock_session_factory)
        wf.ainvoke.assert_awaited_once()
        state = wf.ainvoke.await_args.args[0]
        assert state["tenant_id"] == str(tenant_id)
        assert "crash_event_id" in state
        assert state["docker_host_id"] == event_payload["docker_host_id"]
        assert state["crash_event"] == event_payload
        assert state["analysis"] is None
        assert state["cache_hit"] is False
        assert state["restart_attempted"] is False
        assert state["restart_success"] is None
        assert state["slack_sent"] is False
        assert state["email_sent"] is False
        assert state["call_triggered"] is False
        assert state["recent_crash_count"] == 0


@pytest.mark.asyncio
async def test_process_event_swallows_not_implemented_error(
    tenant_id, event_payload, mock_session_factory, caplog
):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock(side_effect=NotImplementedError("phase 2"))
        # Should not raise; logged as debug/info rather than error.
        await _process_event(event_payload, tenant_id, mock_session_factory)


@pytest.mark.asyncio
async def test_process_event_swallows_other_exceptions(
    tenant_id, event_payload, mock_session_factory, caplog
):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
        await _process_event(event_payload, tenant_id, mock_session_factory)
        assert "Error invoking crash workflow" in caplog.text
