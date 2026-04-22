# Qdrant Crash Memory (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Phase 2 no-op `CrashMemory` stubs with real Qdrant-backed semantic dedup — repeat crashes reuse cached `CrashAnalysis` and skip the LLM call.

**Architecture:** `CrashMemory` wraps `qdrant-client` + `fastembed`. Single `crash_history` collection, 384-dim cosine, `bge-small-en-v1.5` embeddings. Multi-tenant isolation via payload filter on `tenant_id`. `FixAgent.analyze` gets a `tenant_id` parameter; `analyze_crash` node reads it from state. All Qdrant/embedder errors swallow silently — the LLM path is always reachable.

**Tech Stack:** Python 3.11, `qdrant-client`, `fastembed` (ONNX-based, no PyTorch), pytest + pytest-asyncio, `unittest.mock`.

**Spec reference:** `docs/superpowers/specs/2026-04-22-qdrant-memory-design.md`

---

## File Structure

### Files to modify
- `pyproject.toml` — add `fastembed>=0.3.0` to dependencies.
- `src/services/crash_memory.py` — full rewrite with real Qdrant + fastembed wiring.
- `src/agents/fix_agent.py` — add `_build_embedding_text`, new `tenant_id` param on `analyze`, pass tenant + metadata to memory methods.
- `src/agents/conftest.py` (for tests) — update `fix_agent_with_mocks` if mock interface shifts; likely unchanged.
- `src/orchestrator/nodes.py` — `analyze_crash` passes `state["tenant_id"]` to `agent.analyze`.
- `tests/unit/agents/test_fix_agent.py` — update existing tests for new signature; add 3 new tests.
- `tests/unit/orchestrator/test_analyze_crash.py` — update existing tests; add tenant-propagation test.
- `work-tracking/PROGRESS.md` — mark items #15 and #16 as done; add daily log entry.

### Files to create
- `tests/unit/services/__init__.py`
- `tests/unit/services/test_crash_memory.py` — 12 tests for the new real implementation.

### Files to delete
- `tests/unit/agents/test_crash_memory_stubs.py` — obsolete; tests the stub behavior that no longer exists. Superseded by the new services test file.

### Responsibilities per file
- `crash_memory.py` — the only file that talks to Qdrant or fastembed. Everything else is consumers.
- `fix_agent.py` — owns the embedding-text format. Changing the prefix format requires rebuilding the collection.
- `nodes.py → analyze_crash` — the only orchestrator code that knows about tenant_id flowing to the memory.

---

## Task 1: Add `fastembed` dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, locate the `dependencies = [...]` list. Find the line containing `"qdrant-client>=1.9.0"` and add `fastembed` right after it so the vector-DB deps stay grouped:

```toml
    # Vector DB
    "qdrant-client>=1.9.0",
    "fastembed>=0.3.0",
    "langchain-qdrant>=0.2.0",
```

- [ ] **Step 2: Install the new dependency**

Run: `py -3.12 -m pip install "fastembed>=0.3.0"`
Expected: installs fastembed and its ONNX runtime deps. Takes 30–90 seconds.

- [ ] **Step 3: Verify import works**

Run: `py -3.12 -c "from fastembed import TextEmbedding; print('ok')"`
Expected: `ok` printed. No import errors.

(The first actual `TextEmbedding("BAAI/bge-small-en-v1.5")` call will download ~80MB of model weights; that happens at runtime, not at import.)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): add fastembed for open-source embeddings"
```

---

## Task 2: Scaffold `tests/unit/services/` and remove obsolete stub tests

**Files:**
- Create: `tests/unit/services/__init__.py`
- Delete: `tests/unit/agents/test_crash_memory_stubs.py`

- [ ] **Step 1: Create the package init**

Create `tests/unit/services/__init__.py` with one line: `# test package`.

- [ ] **Step 2: Delete the obsolete stubs test**

Remove `tests/unit/agents/test_crash_memory_stubs.py`. Its 3 tests assert behavior that no longer holds (store is no longer a no-op, find_similar doesn't always return None). The replacement tests land in `tests/unit/services/test_crash_memory.py` in Task 3.

- [ ] **Step 3: Verify test collection still works**

Run: `py -3.12 -m pytest tests/unit/ --collect-only 2>&1 | tail -5`
Expected: 63 tests minus 3 obsolete = 60 tests collected. No errors.

- [ ] **Step 4: Run the suite to confirm no regressions**

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: 60 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/services/__init__.py
git rm tests/unit/agents/test_crash_memory_stubs.py
git commit -m "test: scaffold tests/unit/services and drop obsolete crash_memory stubs test"
```

---

## Task 3: Implement `CrashMemory` with Qdrant + fastembed

**Files:**
- Modify: `src/services/crash_memory.py` (full rewrite)
- Create: `tests/unit/services/test_crash_memory.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/services/test_crash_memory.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue

from src.services.crash_memory import CrashMemory


def _make_memory_with_mocks(hit_payload=None, raise_on_search=False, raise_on_upsert=False):
    """Build a CrashMemory with _client and _embedder pre-mocked (bypass _init)."""
    mem = CrashMemory()
    mem._client = MagicMock()
    mem._embedder = MagicMock()
    mem._embedder.embed.return_value = iter([MagicMock(tolist=lambda: [0.1] * 384)])
    mem._ready = True

    if raise_on_search:
        mem._client.search.side_effect = RuntimeError("qdrant down")
    else:
        if hit_payload is not None:
            hit = MagicMock()
            hit.payload = hit_payload
            mem._client.search.return_value = [hit]
        else:
            mem._client.search.return_value = []

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
    analysis = {"root_cause": "OOM", "severity": "high", "category": "oom", "confidence": 0.9, "suggestions": [], "restart_likely_fixes": True}
    mem = _make_memory_with_mocks(hit_payload={"analysis": analysis, "tenant_id": "t1"})
    result = await mem.find_similar("x", tenant_id="t1")
    assert result == analysis


@pytest.mark.asyncio
async def test_find_similar_applies_tenant_filter():
    mem = _make_memory_with_mocks()
    await mem.find_similar("x", tenant_id="tenant-42")
    call = mem._client.search.call_args
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
    assert mem._client.search.call_args.kwargs["score_threshold"] == 0.92

    await mem.find_similar("x", tenant_id="t1", threshold=0.80)
    assert mem._client.search.call_args.kwargs["score_threshold"] == 0.80


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/services/test_crash_memory.py -v`
Expected: FAIL — CrashMemory doesn't have `_client`, `_embedder`, `_ready` attributes, or `_ensure_collection`/`_init` methods yet. Multiple `AttributeError`s.

- [ ] **Step 3: Replace `src/services/crash_memory.py`**

Replace the entire contents:

```python
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config.settings import settings

logger = logging.getLogger("sentinel.services.crash_memory")


class CrashMemory:
    """Qdrant-backed semantic dedup for crash events.

    Multi-tenant via payload filtering on tenant_id. Single shared collection,
    384-dim cosine vectors, bge-small-en-v1.5 embeddings (via fastembed).
    All failures degrade silently so the LLM path is always reachable.
    """

    COLLECTION = "crash_history"
    VECTOR_SIZE = 384
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    def __init__(self):
        self._client: QdrantClient | None = None
        self._embedder: TextEmbedding | None = None
        self._ready: bool = False

    def _init(self) -> None:
        """Lazy-init: connect, load embedder, ensure collection exists."""
        if self._ready:
            return
        self._client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self._embedder = TextEmbedding(model_name=self.MODEL_NAME)
        self._ensure_collection()
        self._ready = True

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist. Idempotent."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self.COLLECTION in existing:
            return
        self._client.create_collection(
            collection_name=self.COLLECTION,
            vectors_config=VectorParams(
                size=self.VECTOR_SIZE, distance=Distance.COSINE
            ),
        )

    def _embed(self, text: str) -> list[float]:
        vec = next(self._embedder.embed([text]))
        return vec.tolist()

    async def find_similar(
        self,
        text: str,
        tenant_id: str,
        threshold: float = 0.92,
    ) -> dict | None:
        try:
            await asyncio.to_thread(self._init)
            vector = await asyncio.to_thread(self._embed, text)
            results = await asyncio.to_thread(
                self._client.search,
                collection_name=self.COLLECTION,
                query_vector=vector,
                query_filter=Filter(
                    must=[FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id),
                    )]
                ),
                limit=1,
                score_threshold=threshold,
            )
        except Exception:
            logger.exception("Qdrant find_similar failed; treating as cache miss")
            return None

        if not results:
            return None
        return results[0].payload.get("analysis")

    async def store(
        self,
        text: str,
        analysis: dict,
        tenant_id: str,
        metadata: dict | None = None,
    ) -> None:
        try:
            await asyncio.to_thread(self._init)
            vector = await asyncio.to_thread(self._embed, text)
            payload = {
                "tenant_id": tenant_id,
                "analysis": analysis,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                payload.update(metadata)
            await asyncio.to_thread(
                self._client.upsert,
                collection_name=self.COLLECTION,
                points=[PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )],
            )
        except Exception:
            logger.exception("Qdrant store failed; analysis remains uncached")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/services/test_crash_memory.py -v`
Expected: PASS (12 tests).

Run full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `72 passed` (60 baseline + 12 new).

- [ ] **Step 5: Commit**

```bash
git add src/services/crash_memory.py tests/unit/services/test_crash_memory.py
git commit -m "feat(services): implement CrashMemory with Qdrant + fastembed"
```

---

## Task 4: Update `FixAgent` signature — add `tenant_id`

**Files:**
- Modify: `src/agents/fix_agent.py`
- Modify: `tests/unit/agents/test_fix_agent.py`

- [ ] **Step 1: Update the test file first (TDD)**

Replace the entire contents of `tests/unit/agents/test_fix_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/agents/test_fix_agent.py -v`
Expected: FAIL — `FixAgent.analyze` takes only one arg today; tenant_id kwarg/positional doesn't exist. Also the new tests for embedding text / metadata will fail.

- [ ] **Step 3: Update `src/agents/fix_agent.py`**

Find the `analyze` method and replace it (the rest of the file — imports, `_minimal_fallback`, `_build_chain`, `get_fix_agent` — is unchanged):

```python
    async def analyze(
        self, crash_event: dict, tenant_id: str
    ) -> tuple[CrashAnalysis, bool]:
        """Analyze a crash event. Returns (analysis, cache_hit)."""
        text = self._build_embedding_text(crash_event)

        cached = await self._memory.find_similar(text, tenant_id)
        if cached is not None:
            return CrashAnalysis.model_validate(cached), True

        try:
            messages = build_analysis_prompt(crash_event)
            analysis = await self._chain.ainvoke(messages)
        except Exception:
            logger.exception("LLM call failed for crash analysis")
            return _minimal_fallback(), False

        try:
            await self._memory.store(
                text,
                analysis.model_dump(),
                tenant_id,
                metadata={
                    "image": crash_event.get("image"),
                    "exit_code": crash_event.get("exit_code"),
                },
            )
        except Exception:
            logger.exception("Failed to store crash analysis in memory")

        return analysis, False

    def _build_embedding_text(self, crash_event: dict) -> str:
        """Build the cache key text: '<image> | exit=<code> | <logs>'."""
        image = crash_event.get("image") or "<unknown>"
        exit_code = crash_event.get("exit_code")
        logs = crash_event.get("logs") or ""
        return f"{image} | exit={exit_code} | {logs}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/agents/test_fix_agent.py -v`
Expected: PASS (9 tests: 6 existing updated + 3 new).

Run full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `72 passed` still (net zero new tests in this task — we replaced the file with the same count plus a few, but existing E2E test may now fail because the orchestrator doesn't pass tenant_id yet. If you see ONE failure in `test_workflow_end_to_end.py` or `test_analyze_crash.py`, that's expected and fixed in Task 5.)

Actually — the existing `analyze_crash` node still calls `agent.analyze(state["crash_event"])` with only one arg. This will now crash with a TypeError. Let me re-state: **expect existing orchestrator tests to FAIL** after this task. Task 5 fixes them.

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -10`
Note: expect failures in `tests/unit/orchestrator/test_analyze_crash.py` and possibly `test_workflow_end_to_end.py`. These are caused by this task's signature change and will be fixed in Task 5.

- [ ] **Step 5: Commit**

```bash
git add src/agents/fix_agent.py tests/unit/agents/test_fix_agent.py
git commit -m "feat(agents): FixAgent.analyze takes tenant_id; add _build_embedding_text"
```

---

## Task 5: Update `analyze_crash` node to pass `tenant_id`

**Files:**
- Modify: `src/orchestrator/nodes.py`
- Modify: `tests/unit/orchestrator/test_analyze_crash.py`

- [ ] **Step 1: Update the test file**

Replace the entire contents of `tests/unit/orchestrator/test_analyze_crash.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_analyze_crash.py -v`
Expected: FAIL — node still calls `agent.analyze(state["crash_event"])` without tenant_id; `assert_awaited_once_with` fails.

- [ ] **Step 3: Update `src/orchestrator/nodes.py`**

Find the `analyze_crash` function and replace it (leave everything else — imports, other nodes, conditional edges — untouched):

```python
async def analyze_crash(state: CrashState) -> dict:
    """Node: call FixAgent to analyze the crash event.

    Phase 3: tenant_id threaded through to CrashMemory for multi-tenant
    cache isolation.
    """
    agent = get_fix_agent()
    analysis, cache_hit = await agent.analyze(
        state["crash_event"], state["tenant_id"]
    )
    return {
        "analysis": analysis.model_dump(),
        "cache_hit": cache_hit,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_analyze_crash.py -v`
Expected: PASS (3 tests).

Run full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `73 passed` (72 from Task 3 + 1 new tenant-propagation test; other test counts unchanged — Task 4 replaced a test file with equal count).

Note: the E2E workflow test (`test_workflow_end_to_end.py`) uses `fake_agent.analyze = AsyncMock(return_value=(canned, False))` which accepts any args — so it will also pass after this task with no further changes.

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/nodes.py tests/unit/orchestrator/test_analyze_crash.py
git commit -m "feat(orchestrator): thread tenant_id from state to FixAgent.analyze"
```

---

## Task 6: Update work tracker

**Files:**
- Modify: `work-tracking/PROGRESS.md`

- [ ] **Step 1: Mark items #15 and #16 as done**

In `work-tracking/PROGRESS.md`, locate the Phase 3 table. Find:

```markdown
| 15 | `src/services/crash_memory.py` → `search()` | Qdrant similarity search (embed crash logs, find similar past crashes) | **High** |
| 16 | `src/services/crash_memory.py` → `store()` | Qdrant storage (embed + store crash analysis results) | **High** |
```

Replace with:

```markdown
| 15 | `src/services/crash_memory.py` → `find_similar()` | Qdrant similarity search (fastembed + bge-small, tenant-filtered) | ✅ **Done** |
| 16 | `src/services/crash_memory.py` → `store()` | Qdrant upsert with tenant_id + analysis + metadata payload | ✅ **Done** |
```

- [ ] **Step 2: Add today's second daily log entry**

Append to the bottom of the `## Daily Log` section (before the `---` separator that precedes "Quick Reference"):

```markdown
### 2026-04-22 (Continued — evening session)
- **Status:** ✅ **Phase 3 items #15 and #16 shipped** — Qdrant semantic cache live. Repeat crashes reuse cached `CrashAnalysis` without calling OpenAI.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-22-qdrant-memory-design.md`
  - Wrote 7-task plan: `docs/superpowers/plans/2026-04-22-qdrant-memory.md`
  - Added `fastembed>=0.3.0` dependency (ONNX-based open embeddings, no PyTorch)
  - Implemented `CrashMemory` with real `QdrantClient` + `TextEmbedding("BAAI/bge-small-en-v1.5")`, single shared `crash_history` collection, cosine distance, tenant filtering via payload `FieldCondition`, 0.92 default threshold
  - Lazy-init + auto-create collection; all failures swallowed so LLM path is always reachable
  - Threaded `tenant_id` through `FixAgent.analyze(crash_event, tenant_id)` and `analyze_crash` node
  - Added `_build_embedding_text` helper: `"<image> | exit=<code> | <logs>"` for stronger similarity signal
  - Deleted obsolete `test_crash_memory_stubs.py`; 12 new tests in `tests/unit/services/test_crash_memory.py`
  - 73 unit tests passing (up from 63)
- **Known deferred items:**
  - Threshold tuning — 0.92 is a starting guess for bge-small; revisit after real crash data accumulates.
  - No TTL / eviction — collection grows forever (fine at portfolio scale).
  - Embedding-text format is hardcoded in `_build_embedding_text`; changing it requires rebuilding the collection.
  - `model_version` not in payload — if Fix Agent prompts/models change, old cache entries remain.
  - Pre-warming the fastembed model in Docker image build for faster first-crash latency.
- **Pick up from here:** **Phase 2 notification agents (items #8–11)** — SlackAgent, EmailAgent, CallAgent, DashboardAgent. Unlocks the `restart_likely_fixes=False → notify_slack` path currently routed to `log`. User-visible value (a real Slack message on crash is a great demo). After notifications: observability/metrics or multi-worker scaling.
```

- [ ] **Step 3: Commit**

```bash
git add work-tracking/PROGRESS.md
git commit -m "docs: mark Phase 3 items 15 and 16 complete in work tracker"
```

---

## Task 7: Smoke test — real Qdrant + cache hit verification

**Files:** none — verification only.

This is the "did the cache actually work" gate. Runs the same crash twice; verifies Run 2 skips the LLM.

- [ ] **Step 1: Start infra (now includes qdrant)**

Run: `docker compose up -d postgres redis qdrant`
Expected: all three services healthy. `docker compose ps` shows postgres, redis, qdrant running.

- [ ] **Step 2: Run migrations (idempotent)**

Run: `py -3.12 -m alembic upgrade head 2>&1 | tail -3`
Expected: "Target database is up to date" or schema applied.

- [ ] **Step 3: Truncate + re-seed**

Run:
```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c "TRUNCATE crash_events, docker_hosts, tenants RESTART IDENTITY CASCADE;"
PYTHONPATH=. py -3.12 scripts/smoke_seed.py
```
Expected: prints `TENANT_ID=<uuid>` and `HOST_ID=<uuid>`.

- [ ] **Step 4: Flush Qdrant collection (clean slate)**

Run: `curl -X DELETE http://localhost:6333/collections/crash_history 2>&1 | tail -2`
Expected: `{"result":true,...}` OR a 404 if the collection doesn't exist yet. Both are fine — CrashMemory auto-creates on first use.

- [ ] **Step 5: Start the worker in the background**

Run (background): `PYTHONPATH=. py -3.12 -u -m src.worker.main`
Expected: logs show `Starting DockerSentinel worker`, listener spawned, status becomes `connected`.

First-run note: on the very first cache operation the worker downloads the fastembed model (~80MB). Allow up to 60 seconds for the first crash to fully resolve.

- [ ] **Step 6: Trigger Run 1 of the crash**

Run: `docker run --name smoke-phase3-run1 busybox sh -c 'echo "ERROR: port 8080 already in use" >&2; exit 1'`
Expected: container exits with code 1.

Wait ~15 seconds (model download + LLM call).

- [ ] **Step 7: Verify Run 1 produced an analyzed row**

Run:
```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "SELECT container_name, cache_hit, LEFT(root_cause, 60) AS root_cause, confidence, resolved_at IS NOT NULL AS resolved FROM crash_events WHERE container_name LIKE 'smoke-phase3%' ORDER BY created_at;"
```
Expected: one row, `cache_hit=f`, `confidence > 0`, `resolved=t`, `root_cause` is an LLM-generated phrase about port conflicts.

Also verify the Qdrant collection has 1 point:
```bash
curl -s http://localhost:6333/collections/crash_history | grep -o '"points_count":[0-9]*'
```
Expected: `"points_count":1`.

- [ ] **Step 8: Trigger Run 2 (same crash, different container name)**

Run: `docker run --name smoke-phase3-run2 busybox sh -c 'echo "ERROR: port 8080 already in use" >&2; exit 1'`
Expected: container exits with code 1.

Wait ~5 seconds.

- [ ] **Step 9: Verify Run 2 was a cache hit**

Run:
```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "SELECT container_name, cache_hit, LEFT(root_cause, 60) AS root_cause, confidence, resolved_at IS NOT NULL AS resolved FROM crash_events WHERE container_name LIKE 'smoke-phase3%' ORDER BY created_at;"
```
Expected: two rows. The second row (`smoke-phase3-run2`) has `cache_hit=t`, `resolved=t`, and its `root_cause` is **identical** to the first row's `root_cause` (the cached analysis was reused).

- [ ] **Step 10: Verify no OpenAI call happened for Run 2**

Check the worker log: count `HTTP Request: POST https://api.openai.com/v1/chat/completions` lines. Expect exactly 1 (from Run 1). Run 2 must NOT generate a new one.

The log file is written to the background task's stdout capture. Find it with the task id, then:
```bash
grep -c "api.openai.com/v1/chat/completions" <worker-output-file>
```
Expected: `1`.

If you see `2` or more, the cache didn't hit — debug why (most likely: embedding text drift, threshold too strict, or tenant filter issue).

- [ ] **Step 11: Tear down**

Run:
```bash
docker rm -f smoke-phase3-run1 smoke-phase3-run2 2>/dev/null
taskkill //F //IM python.exe 2>&1 | head -3
docker compose down
```

- [ ] **Step 12: No commit needed**

Smoke test is verification only. If anything failed at Step 9 or Step 10, capture the worker log and debug before declaring Task 7 done — don't paper over it.

---

## Self-review (completed by the planner)

- **Spec coverage:**
  - `find_similar` with tenant filter, threshold, payload return → Task 3.
  - `store` with tenant_id + analysis + metadata → Task 3.
  - Auto-create collection on first use → Task 3 (`_ensure_collection` + tests).
  - Lazy init + idempotent → Task 3.
  - Error swallowing everywhere → Task 3 (tests for search/embedder/upsert errors).
  - Embedding model = bge-small-en-v1.5, 384 dim → Task 3 constants and tests.
  - `FixAgent.analyze(crash_event, tenant_id)` + `_build_embedding_text` → Task 4.
  - `analyze_crash` threads state["tenant_id"] → Task 5.
  - fastembed dep → Task 1.
  - Tracker update → Task 6.
  - Cache hit smoke test → Task 7.
- **Placeholder scan:** No TBD, TODO. Every code block is complete.
- **Type/name consistency:**
  - `CrashMemory.COLLECTION = "crash_history"` used in tests (Task 3) and CLI curl (Task 7).
  - `VECTOR_SIZE = 384` matches `Distance.COSINE` config in Task 3 test and implementation.
  - `find_similar(text, tenant_id, threshold=0.92)` positional order consistent across Tasks 3, 4.
  - `store(text, analysis, tenant_id, metadata)` positional order consistent.
  - `_build_embedding_text` name consistent in Tasks 4, 5 (tested via the embedded string format).
- **Known caveat not a placeholder:** Task 4's Step 4 expects test failures outside the task's own test file (orchestrator tests break because they haven't been updated to pass tenant_id yet). This is called out explicitly — Task 5 fixes them. If Task 4 is run in isolation without Task 5, the suite will have 1–2 failing tests until Task 5 runs.
