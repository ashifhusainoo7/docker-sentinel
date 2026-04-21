import pytest

from src.orchestrator.nodes import analyze_crash


@pytest.mark.asyncio
async def test_analyze_crash_returns_canned_analysis(initial_state):
    result = await analyze_crash(initial_state)

    assert "analysis" in result
    assert "cache_hit" in result
    assert result["cache_hit"] is False

    a = result["analysis"]
    assert a["restart_likely_fixes"] is True
    assert a["severity"] == "medium"
    assert a["category"] == "unknown"
    assert a["confidence"] == 0.0
    assert isinstance(a["suggestions"], list)
    assert isinstance(a["root_cause"], str)


@pytest.mark.asyncio
async def test_analyze_crash_does_not_mutate_input_state(initial_state):
    snapshot = dict(initial_state)
    await analyze_crash(initial_state)
    assert initial_state == snapshot
