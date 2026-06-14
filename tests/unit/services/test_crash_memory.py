from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.http.models import Distance, FieldCondition, Filter

from src.services.crash_memory import CrashMemory


def _make_memory_with_mocks(hit_payload=None, raise_on_search=False, raise_on_upsert=False):
    """Build a CrashMemory with _client and _embedder pre-mocked (bypass _init)."""
    mem = CrashMemory()
    mem._client = MagicMock()
    mem._embedder = MagicMock()
    mem._embedder.embed.side_effect = lambda texts: iter([MagicMock(tolist=lambda: [0.1] * 384)])
    mem._ready = True

    if raise_on_search:
        mem._client.query_points.side_effect = RuntimeError("qdrant down")
    else:
        response = MagicMock()
        if hit_payload is not None:
            hit = MagicMock()
            hit.payload = hit_payload
            response.points = [hit]
        else:
            response.points = []
        mem._client.query_points.return_value = response

    if raise_on_upsert:
        mem._client.upsert.side_effect = RuntimeError("qdrant down")
    return mem


@pytest.mark.asyncio
async def test_find_similar_returns_none_when_no_match():
    mem = _make_memory_with_mocks()
    result = await mem.find_similar("nginx | exit=137 | oom", tenant_id="t1")
    assert result is None


@pytest.mark.asyncio
async def test_find_similar_returns_payload_on_hit():
    analysis = {
        "root_cause": "OOM", "severity": "high", "category": "oom",
        "confidence": 0.9, "suggestions": [], "restart_likely_fixes": True,
    }
    mem = _make_memory_with_mocks(hit_payload={"analysis": analysis, "tenant_id": "t1"})
    result = await mem.find_similar("x", tenant_id="t1")
    assert result == analysis


@pytest.mark.asyncio
async def test_find_similar_applies_tenant_filter():
    mem = _make_memory_with_mocks()
    await mem.find_similar("x", tenant_id="tenant-42")
    # Asserts the Qdrant API used is query_points (not deprecated search()).
    mem._client.query_points.assert_called_once()
    mem._client.search.assert_not_called()
    call = mem._client.query_points.call_args
    query_filter = call.kwargs["query_filter"]
    assert isinstance(query_filter, Filter)
    assert len(query_filter.must) == 1
    condition = query_filter.must[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "tenant_id"
    assert condition.match.value == "tenant-42"


@pytest.mark.asyncio
async def test_find_similar_threshold_default_and_override():
    mem = _make_memory_with_mocks()
    await mem.find_similar("x", tenant_id="t1")
    assert mem._client.query_points.call_args.kwargs["score_threshold"] == 0.92

    await mem.find_similar("x", tenant_id="t1", threshold=0.80)
    assert mem._client.query_points.call_args.kwargs["score_threshold"] == 0.80


@pytest.mark.asyncio
async def test_find_similar_swallows_qdrant_error():
    mem = _make_memory_with_mocks(raise_on_search=True)
    result = await mem.find_similar("x", tenant_id="t1")
    assert result is None  # degrades to miss


@pytest.mark.asyncio
async def test_find_similar_swallows_embedder_error():
    mem = CrashMemory()
    mem._client = MagicMock()
    mem._embedder = MagicMock()
    mem._embedder.embed.side_effect = RuntimeError("model broken")
    mem._ready = True

    result = await mem.find_similar("x", tenant_id="t1")
    assert result is None


@pytest.mark.asyncio
async def test_store_upserts_vector_with_tenant_and_analysis():
    mem = _make_memory_with_mocks()
    analysis = {"root_cause": "OOM", "severity": "high"}
    await mem.store("x", analysis=analysis, tenant_id="tenant-42")

    call = mem._client.upsert.call_args
    assert call.kwargs["collection_name"] == "crash_history"
    points = call.kwargs["points"]
    assert len(points) == 1
    point = points[0]
    assert point.payload["tenant_id"] == "tenant-42"
    assert point.payload["analysis"] == analysis
    assert "created_at" in point.payload


@pytest.mark.asyncio
async def test_store_includes_optional_metadata():
    mem = _make_memory_with_mocks()
    await mem.store(
        "x",
        analysis={"root_cause": "x"},
        tenant_id="t1",
        metadata={"image": "nginx:1.25", "exit_code": 137},
    )
    point = mem._client.upsert.call_args.kwargs["points"][0]
    assert point.payload["image"] == "nginx:1.25"
    assert point.payload["exit_code"] == 137


@pytest.mark.asyncio
async def test_store_swallows_qdrant_error():
    mem = _make_memory_with_mocks(raise_on_upsert=True)
    # Must not raise.
    await mem.store("x", analysis={"root_cause": "x"}, tenant_id="t1")


def test_ensure_collection_creates_if_missing():
    mem = CrashMemory()
    mem._client = MagicMock()
    collections_result = MagicMock()
    collections_result.collections = []  # no collections yet
    mem._client.get_collections.return_value = collections_result

    mem._ensure_collection()

    mem._client.create_collection.assert_called_once()
    call = mem._client.create_collection.call_args
    assert call.kwargs["collection_name"] == "crash_history"
    params = call.kwargs["vectors_config"]
    assert params.size == 384
    assert params.distance == Distance.COSINE


def test_ensure_collection_skips_if_exists():
    mem = CrashMemory()
    mem._client = MagicMock()
    existing = MagicMock()
    existing.name = "crash_history"
    collections_result = MagicMock()
    collections_result.collections = [existing]
    mem._client.get_collections.return_value = collections_result

    mem._ensure_collection()

    mem._client.create_collection.assert_not_called()


def test_init_is_idempotent():
    with patch("src.services.crash_memory.QdrantClient") as qc, \
         patch("src.services.crash_memory.TextEmbedding") as te:
        fake_client = MagicMock()
        fake_client.get_collections.return_value = MagicMock(collections=[])
        qc.return_value = fake_client
        te.return_value = MagicMock()

        mem = CrashMemory()
        mem._init()
        mem._init()
        mem._init()

        assert qc.call_count == 1
        assert te.call_count == 1
        assert mem._ready is True


def test_init_is_thread_safe_under_concurrent_callers():
    """Concurrent threads entering _init should not double-build the client."""
    import threading as _threading

    with patch("src.services.crash_memory.QdrantClient") as qc, \
         patch("src.services.crash_memory.TextEmbedding") as te:
        fake_client = MagicMock()
        fake_client.get_collections.return_value = MagicMock(collections=[])
        qc.return_value = fake_client
        te.return_value = MagicMock()

        mem = CrashMemory()
        barrier = _threading.Barrier(8)

        def runner():
            barrier.wait()  # release all threads simultaneously
            mem._init()

        threads = [_threading.Thread(target=runner) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert qc.call_count == 1
        assert te.call_count == 1


@pytest.mark.asyncio
async def test_store_drops_reserved_metadata_keys():
    """metadata must not be allowed to overwrite tenant_id, analysis, or created_at."""
    mem = _make_memory_with_mocks()
    analysis = {"root_cause": "OOM"}
    await mem.store(
        "x",
        analysis=analysis,
        tenant_id="tenant-42",
        metadata={
            "tenant_id": "attacker",       # reserved — must be dropped
            "analysis": {"root_cause": "injected"},  # reserved — must be dropped
            "created_at": "1999-01-01",    # reserved — must be dropped
            "image": "nginx:1.25",         # allowed
        },
    )
    point = mem._client.upsert.call_args.kwargs["points"][0]
    assert point.payload["tenant_id"] == "tenant-42"
    assert point.payload["analysis"] == analysis
    assert point.payload["created_at"] != "1999-01-01"
    assert point.payload["image"] == "nginx:1.25"
