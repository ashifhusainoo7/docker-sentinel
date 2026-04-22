from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.crash_event import CrashAnalysis


@pytest.fixture(autouse=True)
def reset_fix_agent_singleton():
    """Prevents singleton state from leaking between tests."""
    import src.agents.fix_agent as mod

    mod._agent_instance = None
    yield
    mod._agent_instance = None


@pytest.fixture
def sample_crash_analysis() -> CrashAnalysis:
    return CrashAnalysis(
        restart_likely_fixes=True,
        root_cause="OOM killed during startup",
        severity="high",
        category="oom",
        suggestions=["Increase memory limit", "Investigate leak"],
        confidence=0.82,
    )


@pytest.fixture
def sample_crash_event() -> dict:
    return {
        "docker_host_id": "00000000-0000-0000-0000-000000000001",
        "container_name": "web-1",
        "container_id": "abc123",
        "image": "nginx:1.25",
        "exit_code": 137,
        "logs": "out of memory: Killed process 42 (nginx)",
        "event_type": "die",
        "event_timestamp": "2026-04-22T10:00:00+00:00",
    }


@pytest.fixture
def fix_agent_with_mocks(sample_crash_analysis):
    """Return a FixAgent with mocked memory and chain.

    Patches ChatOpenAI at import time so __init__ doesn't try to
    instantiate a real client. Replaces _memory and _chain on the
    instance with AsyncMock-backed stubs.
    """
    with patch("src.agents.fix_agent.ChatOpenAI"):
        from src.agents.fix_agent import FixAgent

        agent = FixAgent()

    agent._memory = MagicMock()
    agent._memory.find_similar = AsyncMock(return_value=None)
    agent._memory.store = AsyncMock(return_value=None)

    agent._chain = MagicMock()
    agent._chain.ainvoke = AsyncMock(return_value=sample_crash_analysis)

    return agent
