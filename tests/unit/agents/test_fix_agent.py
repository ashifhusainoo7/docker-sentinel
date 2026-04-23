from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.crash_event import CrashAnalysis


TENANT = "tenant-abc"


@pytest.mark.asyncio
async def test_analyze_cache_hit_returns_cached_and_skips_llm(
    fix_agent_with_mocks, sample_crash_analysis, sample_crash_event
):
    agent = fix_agent_with_mocks
    agent._memory.find_similar = AsyncMock(
        return_value=sample_crash_analysis.model_dump()
    )

    analysis, cache_hit = await agent.analyze(sample_crash_event, TENANT)

    assert cache_hit is True
    assert analysis.root_cause == sample_crash_analysis.root_cause
    agent._chain.ainvoke.assert_not_awaited()
    agent._memory.store.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_cache_miss_calls_llm_and_stores(
    fix_agent_with_mocks, sample_crash_analysis, sample_crash_event
):
    agent = fix_agent_with_mocks

    analysis, cache_hit = await agent.analyze(sample_crash_event, TENANT)

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

    analysis, cache_hit = await agent.analyze(sample_crash_event, TENANT)

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

    await agent.analyze(sample_crash_event, TENANT)

    agent._memory.store.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_store_failure_still_returns_analysis(
    fix_agent_with_mocks, sample_crash_analysis, sample_crash_event
):
    agent = fix_agent_with_mocks
    agent._memory.store = AsyncMock(side_effect=RuntimeError("qdrant down"))

    analysis, cache_hit = await agent.analyze(sample_crash_event, TENANT)

    assert cache_hit is False
    assert analysis.root_cause == sample_crash_analysis.root_cause


@pytest.mark.asyncio
async def test_analyze_builds_embedding_text_with_image_and_exit_code(
    fix_agent_with_mocks, sample_crash_event
):
    agent = fix_agent_with_mocks
    await agent.analyze(sample_crash_event, TENANT)

    # find_similar is the first call that receives the embedding text
    text_arg = agent._memory.find_similar.await_args.args[0]
    assert sample_crash_event["image"] in text_arg
    assert f"exit={sample_crash_event['exit_code']}" in text_arg
    assert sample_crash_event["logs"] in text_arg


@pytest.mark.asyncio
async def test_analyze_passes_tenant_id_to_memory(
    fix_agent_with_mocks, sample_crash_event
):
    agent = fix_agent_with_mocks
    await agent.analyze(sample_crash_event, TENANT)

    # tenant_id is the second positional arg to find_similar and store
    assert agent._memory.find_similar.await_args.args[1] == TENANT
    assert agent._memory.store.await_args.args[2] == TENANT


@pytest.mark.asyncio
async def test_analyze_passes_image_and_exit_code_metadata_to_store(
    fix_agent_with_mocks, sample_crash_event
):
    agent = fix_agent_with_mocks
    await agent.analyze(sample_crash_event, TENANT)

    metadata = agent._memory.store.await_args.kwargs["metadata"]
    assert metadata["image"] == sample_crash_event["image"]
    assert metadata["exit_code"] == sample_crash_event["exit_code"]


def test_get_fix_agent_returns_singleton():
    with patch("src.agents.fix_agent.ChatOpenAI"):
        from src.agents.fix_agent import get_fix_agent

        a1 = get_fix_agent()
        a2 = get_fix_agent()
        assert a1 is a2
