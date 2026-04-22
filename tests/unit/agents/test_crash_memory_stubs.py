import pytest

from src.services.crash_memory import CrashMemory


@pytest.mark.asyncio
async def test_find_similar_returns_none_in_phase_2():
    memory = CrashMemory()
    result = await memory.find_similar("some logs")
    assert result is None


@pytest.mark.asyncio
async def test_find_similar_accepts_threshold_arg():
    memory = CrashMemory()
    result = await memory.find_similar("some logs", threshold=0.85)
    assert result is None


@pytest.mark.asyncio
async def test_store_is_noop_in_phase_2():
    memory = CrashMemory()
    result = await memory.store("some logs", {"root_cause": "x"})
    assert result is None
