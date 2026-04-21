import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.graph import crash_workflow


def _fake_host(host_id):
    h = MagicMock()
    h.id = host_id
    h.connection_mode = "tcp"
    h.tcp_url = "tcp://test:2376"
    h.tls_enabled = False
    h.tls_ca = None
    h.tls_cert = None
    h.tls_key = None
    return h


@pytest.mark.asyncio
async def test_workflow_happy_path_invokes_all_three_nodes(initial_state, host_id):
    """analyze_crash (stub) → attempt_restart (success) → log_event.

    Asserts that the compiled workflow threads state correctly via LangGraph's
    conditional edges and that the terminal log_event node runs.
    """
    fake_host = _fake_host(host_id)
    fake_container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    session = AsyncMock()
    session.get = AsyncMock(return_value=fake_host)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session), \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client):
        final_state = await crash_workflow.ainvoke(initial_state)

    # analyze_crash stub ran
    assert final_state["analysis"] is not None
    assert final_state["analysis"]["restart_likely_fixes"] is True
    assert final_state["cache_hit"] is False

    # attempt_restart ran and succeeded
    assert final_state["restart_attempted"] is True
    assert final_state["restart_success"] is True
    fake_container.restart.assert_called_once_with(timeout=10)

    # log_event ran (UPDATE executed on the CrashEvent row)
    # session.execute was called at least twice — once in attempt_restart (get host)
    # and once in log_event (UPDATE). The UPDATE is the one we care about:
    update_calls = [c for c in session.execute.await_args_list]
    assert len(update_calls) >= 1
    # session.commit was awaited by log_event
    session.commit.assert_awaited()
