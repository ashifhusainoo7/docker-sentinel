from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.nodes import analyze_crash
from src.schemas.crash_event import CrashAnalysis


def _sample_analysis() -> CrashAnalysis:
    return CrashAnalysis(
        restart_likely_fixes=True,
        root_cause="dependency not ready",
        severity="high",
        category="dependency_failure",
        suggestions=["Add healthcheck", "Delay start"],
        confidence=0.78,
    )


@pytest.mark.asyncio
async def test_analyze_crash_calls_fix_agent_and_returns_analysis(initial_state):
    analysis = _sample_analysis()

    fake_agent = MagicMock()
    fake_agent.analyze = AsyncMock(return_value=(analysis, False))

    with patch("src.orchestrator.nodes.get_fix_agent", return_value=fake_agent):
        result = await analyze_crash(initial_state)

    fake_agent.analyze.assert_awaited_once_with(
        initial_state["crash_event"], initial_state["tenant_id"]
    )
    assert result["analysis"]["root_cause"] == "dependency not ready"
    assert result["analysis"]["category"] == "dependency_failure"
    assert result["cache_hit"] is False


@pytest.mark.asyncio
async def test_analyze_crash_propagates_cache_hit(initial_state):
    analysis = _sample_analysis()

    fake_agent = MagicMock()
    fake_agent.analyze = AsyncMock(return_value=(analysis, True))

    with patch("src.orchestrator.nodes.get_fix_agent", return_value=fake_agent):
        result = await analyze_crash(initial_state)

    assert result["cache_hit"] is True
    assert result["analysis"]["confidence"] == 0.78


@pytest.mark.asyncio
async def test_analyze_crash_passes_tenant_id_from_state(initial_state):
    """Asserts the tenant_id threaded from state reaches FixAgent.analyze."""
    analysis = _sample_analysis()

    fake_agent = MagicMock()
    fake_agent.analyze = AsyncMock(return_value=(analysis, False))

    with patch("src.orchestrator.nodes.get_fix_agent", return_value=fake_agent):
        await analyze_crash(initial_state)

    args = fake_agent.analyze.await_args.args
    assert args[1] == initial_state["tenant_id"]
