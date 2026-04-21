from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.nodes import log_event


def _state_with_analysis(base_state, **overrides):
    state = dict(base_state)
    state.update({
        "analysis": {
            "restart_likely_fixes": True,
            "root_cause": "OOM killed",
            "severity": "high",
            "category": "oom",
            "suggestions": ["increase memory limit", "investigate leak"],
            "confidence": 0.85,
        },
        "cache_hit": False,
        "restart_attempted": True,
        "restart_success": True,
        "slack_sent": False,
        "email_sent": False,
        "call_triggered": False,
    })
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_log_event_updates_row_with_full_analysis(initial_state):
    state = _state_with_analysis(initial_state)
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session):
        result = await log_event(state)

    assert result == {}
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()

    # Inspect the UPDATE values passed through sqlalchemy's update().values(...)
    stmt = session.execute.await_args.args[0]
    values = stmt.compile().params
    assert values["root_cause"] == "OOM killed"
    assert values["category"] == "oom"
    assert values["severity"] == "high"
    assert values["confidence"] == 0.85
    assert values["suggestions"] == ["increase memory limit", "investigate leak"]
    assert values["restart_attempted"] is True
    assert values["restart_success"] is True


@pytest.mark.asyncio
async def test_log_event_handles_none_analysis(initial_state):
    state = dict(initial_state)
    state["analysis"] = None
    state["restart_attempted"] = False

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session):
        await log_event(state)

    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    values = stmt.compile().params
    assert values["root_cause"] is None
    assert values["category"] is None
    assert values["suggestions"] == []
    assert values["restart_attempted"] is False
