from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.crash_event import CrashAnalysis


@pytest.mark.asyncio
async def test_analyze_cache_hit_returns_cached_and_skips_llm(
    fix_agent_with_mocks, sample_crash_analysis, sample_crash_event
):
    agent = fix_agent_with_mocks
    agent._memory.find_similar = AsyncMock(
        return_value=sample_crash_analysis.model_dump()
    )

    analysis, cache_hit = await agent.analyze(sample_crash_event)

    assert cache_hit is True
    assert analysis.root_cause == sample_crash_analysis.root_cause
    agent._chain.ainvoke.assert_not_awaited()
    agent._memory.store.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_cache_miss_calls_llm_and_stores(
    fix_agent_with_mocks, sample_crash_analysis, sample_crash_event
):
    agent = fix_agent_with_mocks
    # default find_similar returns None (set up in conftest)

    analysis, cache_hit = await agent.analyze(sample_crash_event)

    assert cache_hit is False
    assert analysis.root_cause == sample_crash_analysis.root_cause
    agent._chain.ainvoke.assert_awaited_once()
    agent._memory.store.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_llm_failure_returns_minimal_fallback(
    fix_agent_with_mocks, sample_crash_event
):
    agent = fix_agent_with_mocks
    agent._chain.ainvoke = AsyncMock(side_effect=RuntimeError("openai down"))

    analysis, cache_hit = await agent.analyze(sample_crash_event)

    assert cache_hit is False
    assert analysis.confidence == 0.0
    assert analysis.category == "unknown"
    assert "LLM unavailable" in analysis.root_cause
    assert analysis.restart_likely_fixes is False


@pytest.mark.asyncio
async def test_analyze_llm_failure_skips_store(
    fix_agent_with_mocks, sample_crash_event
):
    agent = fix_agent_with_mocks
    agent._chain.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

    await agent.analyze(sample_crash_event)

    agent._memory.store.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_store_failure_still_returns_analysis(
    fix_agent_with_mocks, sample_crash_analysis, sample_crash_event
):
    """Memory.store failing should not fail the whole call."""
    agent = fix_agent_with_mocks
    agent._memory.store = AsyncMock(side_effect=RuntimeError("qdrant down"))

    analysis, cache_hit = await agent.analyze(sample_crash_event)

    assert cache_hit is False
    assert analysis.root_cause == sample_crash_analysis.root_cause


def test_get_fix_agent_returns_singleton():
    with patch("src.agents.fix_agent.ChatOpenAI"):
        from src.agents.fix_agent import get_fix_agent

        a1 = get_fix_agent()
        a2 = get_fix_agent()
        assert a1 is a2
