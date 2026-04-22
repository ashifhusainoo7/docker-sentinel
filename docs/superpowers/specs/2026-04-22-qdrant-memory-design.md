# Qdrant Crash Memory (Phase 3) — Design

**Date:** 2026-04-22
**Scope:** Phase 3 items #15 and #16 from `work-tracking/PROGRESS.md` — replace the Phase 2 no-op `CrashMemory` stubs with real Qdrant-backed vector similarity search. The goal is semantic dedup: when the same crash reoccurs, skip the LLM call and reuse the cached `CrashAnalysis`.

Out of scope:
- Notification agents (items #8–11).
- Re-embedding historical `crash_events` rows on first deploy.
- Collection migrations / schema versioning beyond "auto-create on first use."
- TTL / eviction / max-size policies.

## Goals

1. A repeat crash (same image, same exit code, similar logs) reuses the cached `CrashAnalysis` without calling OpenAI.
2. Multi-tenant isolation: tenant A never sees tenant B's cached analyses.
3. Any Qdrant failure degrades silently to Phase-2 behavior (cache always misses, store is skipped). The LLM path stays load-bearing, not the cache.
4. No new environment variables; existing `QDRANT_HOST` / `QDRANT_PORT` settings cover the integration.

## Non-goals

- Exact-match caching (we use vector similarity, not log equality).
- Cross-tenant analysis sharing.
- Cache invalidation when Fix Agent's prompt/model changes.
- Sub-50ms cache latency. 100–200ms is acceptable.

## Architecture

```
FixAgent.analyze(crash_event, tenant_id)      ← tenant_id is NEW arg
          ↓
   build embedding text:
   f"{image} | exit={exit_code} | {logs}"
          ↓
   CrashMemory.find_similar(text, tenant_id, threshold=0.92)
          ↓
   ┌────────────────────────────────────────────────┐
   │ 1. Embed text with fastembed bge-small-en-v1.5 │ → 384-dim vec
   │ 2. QdrantClient.search(                         │
   │      collection="crash_history",                │
   │      query_vector=vec,                          │
   │      query_filter=Filter(must=[                 │
   │        FieldCondition(key="tenant_id",          │
   │          match=MatchValue(value=tenant_id))]),  │
   │      limit=1, score_threshold=0.92)             │
   └────────────────────┬───────────────────────────┘
                        ↓
            hit → return payload["analysis"]
                        ↓ miss / error
                        ↓
              FixAgent falls through to LLM
                        ↓
   CrashMemory.store(text, analysis, tenant_id, metadata)
                        ↓
   ┌────────────────────────────────────────────────┐
   │ 1. Embed text with fastembed                    │
   │ 2. QdrantClient.upsert(                         │
   │      collection="crash_history",                │
   │      points=[PointStruct(                       │
   │        id=uuid4(), vector=vec,                  │
   │        payload={tenant_id, analysis, created_at,│
   │                 image, exit_code})])            │
   └────────────────────────────────────────────────┘
```

**Flow invariants:**

- LLM is always the fallback. Cache miss, Qdrant down, embedding failure — all produce the same observable behavior (call OpenAI, return analysis).
- `cache_hit=True` in state means "skipped the LLM." `cache_hit=False` means "LLM was called, regardless of whether store() succeeded."

## Key design decisions

### Single-collection multi-tenancy (shared collection, tenant filter)

One Qdrant collection, `crash_history`. Points are tagged with `tenant_id` in the payload. Searches use Qdrant's `must` filter to scope to a tenant.

**Why:** Matches the rest of the app's multi-tenancy pattern (shared schema, `tenant_id` column). Simpler ops than per-tenant collections, scales fine at portfolio size, and Qdrant's HNSW index handles payload filtering efficiently.

### fastembed + `BAAI/bge-small-en-v1.5` (384 dims)

Open-source embeddings via Qdrant's official `fastembed` package (ONNX-based, no PyTorch dependency).

**Why:** Zero per-embedding cost (embeddings scale with crash volume and would dominate LLM spend in a real SaaS). `bge-small-en-v1.5` is competitive on short-text similarity benchmarks. `fastembed`'s ONNX runtime keeps the install footprint ~300MB instead of PyTorch's ~2GB. Portfolio story: "We use OpenAI for reasoning but open embeddings for storage because embedding workloads scale with crash rate."

Model name is inlined as a constant in the code — changing models requires rebuilding the collection, so config-izing it would be misleading.

### What we embed: `"{image} | exit={exit_code} | {logs}"`

Structured prefix, not raw logs.

**Why:** Two crashes of the same image at the same exit code almost always have the same root cause. Prefixing with those fields gives the embedding a strong signal and pulls semantically-similar crashes above the threshold even when log text drifts. Free (a few tokens) and meaningfully better than raw logs.

### 0.92 cosine similarity threshold

Default threshold carried over from the original skeleton design.

**Why:** Conservative — only matches when crashes are essentially identical. With bge-small the exact sweet spot may differ from OpenAI's embeddings. We document this as a known tuning target; portfolio scale won't force an answer.

### Auto-create collection on first use

`_ensure_collection` is called by `_init` and is idempotent. Checks `get_collections`; creates if absent.

**Why:** Simpler than a migration for a portfolio project. Idempotent, safe to run every startup. Production would replace this with an explicit schema migration step.

### Cache is never load-bearing

All Qdrant/fastembed calls inside `find_similar` and `store` are wrapped in `try/except Exception` that swallows failures and logs. `find_similar` returns `None` (miss). `store` returns silently. The LLM path continues unchanged.

**Why:** A broken cache should degrade performance, not correctness. This matches the FixAgent's existing defensive posture.

## Component specifications

### `CrashMemory` (`src/services/crash_memory.py` — full rewrite)

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

    Multi-tenant via payload filtering. Single shared collection
    `crash_history`, 384-dim vectors (bge-small-en-v1.5), cosine distance.
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

### `FixAgent` signature updates (`src/agents/fix_agent.py`)

Add a helper `_build_embedding_text` and pass `tenant_id` to both memory methods:

```python
def _build_embedding_text(self, crash_event: dict) -> str:
    image = crash_event.get("image") or "<unknown>"
    exit_code = crash_event.get("exit_code")
    logs = crash_event.get("logs") or ""
    return f"{image} | exit={exit_code} | {logs}"

async def analyze(
    self, crash_event: dict, tenant_id: str
) -> tuple[CrashAnalysis, bool]:
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
```

### Orchestrator wiring (`src/orchestrator/nodes.py`)

```python
async def analyze_crash(state: CrashState) -> dict:
    agent = get_fix_agent()
    analysis, cache_hit = await agent.analyze(
        state["crash_event"], state["tenant_id"]
    )
    return {"analysis": analysis.model_dump(), "cache_hit": cache_hit}
```

## Error handling

| Failure | Where | Response |
|---|---|---|
| Qdrant unreachable | `_init`, `search`, `upsert` | Caught in find_similar → None (miss). Caught in store → swallowed. Logged via `logger.exception`. |
| Collection missing | `_ensure_collection` | Auto-created. |
| Collection exists with wrong vector size | `_ensure_collection` / `upsert` | Not auto-fixed. upsert raises dim mismatch → caught in store's except. Operator drops the collection manually. |
| fastembed model download fails | `TextEmbedding.__init__` | Caught → miss/skip. Retries on next crash. |
| fastembed embed raises | `_embed` | Caught → miss/skip. |
| tenant_id empty string | Qdrant filter | Filter matches nothing → miss. No crash. |

## Configuration

No new env vars. Uses existing `settings.qdrant_host` / `settings.qdrant_port`.

Inlined constants in `CrashMemory`:
- `COLLECTION = "crash_history"`
- `VECTOR_SIZE = 384`
- `MODEL_NAME = "BAAI/bge-small-en-v1.5"`
- Default `threshold=0.92` (caller can override).

## Dependencies

Add to `pyproject.toml`:
```
fastembed>=0.3.0
```

Already present: `qdrant-client>=1.9.0`, `langchain-qdrant>=0.2.0` (unused by this design but left in place).

**Footprint:** `fastembed` + ONNX Runtime ≈ 300MB install. First use downloads ~80MB model weights to `~/.cache/fastembed/`. Persistent across restarts. For containerized deploys, mount a volume or pre-warm the cache in the Dockerfile.

## Docker compose

Existing `qdrant` service in `docker-compose.yml` (ports 6333/6334) is sufficient. No compose changes.

## Testing

### Unit tests (`tests/unit/services/test_crash_memory.py` — new file, all Qdrant + fastembed mocked)

- `test_find_similar_returns_none_when_no_match`
- `test_find_similar_returns_payload_on_hit`
- `test_find_similar_applies_tenant_filter`
- `test_find_similar_threshold_default_and_override`
- `test_find_similar_swallows_qdrant_error`
- `test_find_similar_swallows_embedder_error`
- `test_store_upserts_vector_with_tenant_and_analysis`
- `test_store_includes_optional_metadata`
- `test_store_swallows_qdrant_error`
- `test_ensure_collection_creates_if_missing`
- `test_ensure_collection_skips_if_exists`
- `test_init_is_idempotent`

### Unit test updates (`tests/unit/agents/test_fix_agent.py`)

- Update existing tests for the new `analyze(crash_event, tenant_id)` signature.
- Add `test_analyze_builds_embedding_text_with_image_and_exit_code`.
- Add `test_analyze_passes_tenant_id_to_memory`.
- Add `test_analyze_passes_image_and_exit_code_metadata_to_store`.

### Unit test updates (`tests/unit/orchestrator/test_analyze_crash.py`)

- Update existing tests to assert `agent.analyze` is called with `(crash_event, tenant_id)`.
- Add `test_analyze_crash_passes_tenant_id_from_state`.

### No real-Qdrant / real-fastembed tests in CI

Same policy as Phase 2: CI never downloads the embedding model or hits a running Qdrant. Real verification happens in the smoke test below.

### Smoke test — the "did it actually work" gate

Run the SAME crash twice with real Qdrant + real fastembed + real OpenAI:

**Run 1:** `docker run --name smoke-phase3 busybox sh -c 'echo "port 8080 in use" >&2; exit 1'`
- Expected: `crash_events` row with LLM analysis, `cache_hit=false`.
- Worker log: one OpenAI chat-completion request.

**Run 2:** Same command, same container name (after `docker rm`).
- Expected: new `crash_events` row with the same analysis, `cache_hit=true`.
- Worker log: ZERO OpenAI chat-completion requests for Run 2.

### Expected totals

- +12 `crash_memory` tests.
- +3 `fix_agent` signature tests.
- +1 `analyze_crash` tenant-propagation test.
- Updates to ~3 existing tests (no net increase from updates).

Current suite: 63 tests. After this session: ~79 tests.

## Acceptance criteria

1. A crash analyzed by the worker produces a Qdrant point with the correct payload (`tenant_id`, `analysis`, `created_at`, `image`, `exit_code`).
2. A repeat of the same crash under the same tenant reuses the cached analysis (`cache_hit=true` in the DB row, no OpenAI request in the worker log).
3. A crash under a different `tenant_id` never matches the first tenant's cached entry (verified by filter — can be spot-checked in the smoke test by seeding two tenants).
4. Killing the Qdrant container mid-run degrades cleanly: the worker still processes events via the LLM path, no workflow crashes.
5. All 79 unit tests pass with mocked Qdrant + fastembed.

## Known deferred items

- Threshold tuning (0.92 with bge-small may need adjustment after real data).
- TTL / eviction / max-size.
- Embedding text versioning (current prefix format is hardcoded; if we change it, old entries won't match new queries).
- Analysis invalidation when Fix Agent's model changes (add `model_version` to payload for Phase 4 when we care).
- Pre-warming fastembed model in Docker image build.
