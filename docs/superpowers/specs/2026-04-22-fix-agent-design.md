# Fix Agent (Phase 2) — Design

**Date:** 2026-04-22
**Scope:** Phase 2 item #7 from `work-tracking/PROGRESS.md` — replace the `analyze_crash` stub body with a real LangChain-driven OpenAI call that returns a structured `CrashAnalysis`. Stub `CrashMemory` (Qdrant) stays as a no-op; Phase 3 fills it in.

Out of scope:
- Qdrant integration — `CrashMemory` methods return None / pass.
- Notification agents (Slack, Email, Call) — Phase 2 items #8–11.
- Populating `CrashEvent.llm_provider` / `llm_latency_ms` (minor follow-up).

## Goals

1. A real crash produces a `CrashEvent` row with LLM-generated `root_cause`, `severity`, `category`, `suggestions`.
2. OpenAI outages gracefully degrade — workflow still completes, row persists with `confidence=0.0`.
3. Phase 3 can plug in real Qdrant without touching `FixAgent` or the orchestrator node.
4. No real OpenAI calls in unit tests.

## Non-goals

- Prompt engineering / versioning / A/B testing.
- Real Qdrant embedding or similarity search.
- Metrics, Prometheus counters.
- Multi-tenant prompt customization.
- Caching beyond Qdrant.

## Architecture

```
  analyze_crash node (src/orchestrator/nodes.py)
              ↓
       get_fix_agent()   ← module-level singleton
              ↓
        FixAgent.analyze(crash_event)
              ↓
    ┌────────────────────────────────────┐
    │ 1. CrashMemory.find_similar(logs)  │  Phase 2 stub: always None
    │    (stub)                           │  Phase 3: real Qdrant query
    └────────────────┬───────────────────┘
                     ↓ cache miss
    ┌────────────────────────────────────┐
    │ 2. build_analysis_prompt(event)     │  pure function
    └────────────────┬───────────────────┘
                     ↓
    ┌────────────────────────────────────┐
    │ 3. chain.ainvoke(messages)          │
    │    = gpt-4o-mini                    │
    │        .with_fallbacks([gpt-4o])    │
    │        .with_structured_output(     │
    │          CrashAnalysis)             │
    └────────────────┬───────────────────┘
          success    │     both-fail
                     │          ↓
                     │    _minimal_fallback()
                     │    (confidence=0.0)
                     ↓
    ┌────────────────────────────────────┐
    │ 4. CrashMemory.store(logs, result)  │  Phase 2 stub: no-op
    │    (stub — skipped on failure)      │  Phase 3: embed + upsert
    └────────────────┬───────────────────┘
                     ↓
        returns (CrashAnalysis, cache_hit: bool)
                     ↓
    analyze_crash returns:
    { "analysis": analysis.model_dump(), "cache_hit": <bool> }
```

## Key design decisions

### OpenAI via LangChain (not raw SDK)

Skeleton already commits to LangChain (`langchain-openai` is a dep). `with_structured_output(CrashAnalysis)` gives Pydantic validation for free. `with_fallbacks(...)` gives the primary→fallback pattern without custom retry code.

### gpt-4o-mini primary + gpt-4o fallback

Both OpenAI — this session's decision after the user moved the project from Anthropic to OpenAI as main LLM.
- Primary: ~$0.15/1M input tokens, fast, sufficient for >99% of crash analyses.
- Fallback: ~10× cost but only hit when primary fails (rate limit, timeout, transient error).
- Why both-OpenAI (not a cross-provider fallback): simpler, demonstrates the production pattern without multi-vendor credentials. Full OpenAI outage is handled by the minimal-fallback path below.

### Module-level singleton, lazy-initialized

`get_fix_agent()` returns a shared `FixAgent` instance built on first call. Prevents rebuilding the LangChain chain per crash event. Thread-safe in practice because the orchestrator nodes run in a single asyncio loop (no lock needed at portfolio scale).

### Minimal-fallback analysis when both models fail

`FixAgent.analyze` catches any exception from `chain.ainvoke`, logs via `logger.exception`, returns a `CrashAnalysis` with `confidence=0.0`, `category="unknown"`, `root_cause="LLM unavailable — manual investigation required"`, `restart_likely_fixes=False`.

`confidence=0.0` is the visible signal that something went wrong — the UI can filter or surface these without a schema change. `restart_likely_fixes=False` is the safe default: "we don't know, don't restart blindly."

We do NOT call `CrashMemory.store()` for minimal fallbacks — no value caching a "we don't know" result.

### Logs truncation at prompt-build time

Listener already caps log capture at 200 lines, but the prompt builder defensively re-truncates to the last 200. Keeps the prompt bounded regardless of upstream changes.

### `CrashMemory` stays on its current class shape

`find_similar` and `store` become `async def` methods that return `None` / do nothing. No `NotImplementedError`. Phase 3 replaces the bodies; callers don't change.

## Component specifications

### `FixAgent` (`src/agents/fix_agent.py` — modified)

```python
import logging

from langchain_openai import ChatOpenAI

from src.agents._prompts import build_analysis_prompt
from src.schemas.crash_event import CrashAnalysis
from src.services.crash_memory import CrashMemory

logger = logging.getLogger("sentinel.agents.fix")


def _minimal_fallback() -> CrashAnalysis:
    return CrashAnalysis(
        restart_likely_fixes=False,
        root_cause="LLM unavailable — manual investigation required",
        severity="medium",
        category="unknown",
        suggestions=["Check LLM provider status", "Review logs manually"],
        confidence=0.0,
    )


class FixAgent:
    """Analyzes crash events via OpenAI, with Qdrant cache lookup.

    Phase 2: CrashMemory stub returns None → every event hits the LLM.
    Phase 3: Qdrant similarity check gates the LLM call.
    """

    def __init__(self):
        self._memory = CrashMemory()
        self._chain = self._build_chain()

    def _build_chain(self):
        primary = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            timeout=30,
        ).with_structured_output(CrashAnalysis)
        fallback = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            timeout=30,
        ).with_structured_output(CrashAnalysis)
        return primary.with_fallbacks([fallback])

    async def analyze(self, crash_event: dict) -> tuple[CrashAnalysis, bool]:
        """Analyze a crash event. Returns (analysis, cache_hit)."""
        logs = crash_event.get("logs") or ""

        cached = await self._memory.find_similar(logs)
        if cached is not None:
            return CrashAnalysis.model_validate(cached), True

        try:
            messages = build_analysis_prompt(crash_event)
            analysis = await self._chain.ainvoke(messages)
        except Exception:
            logger.exception("LLM call failed for crash analysis")
            return _minimal_fallback(), False

        try:
            await self._memory.store(logs, analysis.model_dump())
        except Exception:
            logger.exception("Failed to store crash analysis in memory")
            # Don't fail the whole call — we have the analysis, caching is best-effort.

        return analysis, False


_agent_instance: FixAgent | None = None


def get_fix_agent() -> FixAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = FixAgent()
    return _agent_instance
```

### Prompt builder (`src/agents/_prompts.py` — new file)

```python
def build_analysis_prompt(crash_event: dict) -> list[dict]:
    """Build the LangChain messages list from a crash event dict.

    Pure function — no side effects, trivially testable.
    """
    container = crash_event.get("container_name") or "<unknown>"
    image = crash_event.get("image") or "<unknown>"
    exit_code = crash_event.get("exit_code")
    event_type = crash_event.get("event_type") or "die"
    logs = crash_event.get("logs") or "<no logs captured>"

    log_lines = logs.splitlines()
    if len(log_lines) > 200:
        log_lines = log_lines[-200:]
    logs_text = "\n".join(log_lines) if log_lines else "<no logs captured>"

    system = (
        "You are a Docker crash analyst. Given a container's crash event and "
        "the last log lines before it exited, produce a structured diagnosis. "
        "Be concise and specific. If the logs are insufficient, set confidence low."
    )
    user = (
        f"Container: {container}\n"
        f"Image: {image}\n"
        f"Exit code: {exit_code}\n"
        f"Event: {event_type}\n\n"
        f"Logs (last 200 lines):\n"
        f"---\n{logs_text}\n---\n\n"
        f"Produce a CrashAnalysis. Set restart_likely_fixes=True only if the "
        f"root cause is transient (OOM, network, dependency startup race). "
        f"Set it to False for config errors, code bugs, or missing dependencies."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
```

### `CrashMemory` stubs (`src/services/crash_memory.py` — modified)

```python
class CrashMemory:
    """Qdrant vector cache for crash similarity matching.

    Phase 2: stubs — find_similar always returns None, store is a no-op.
    Phase 3: real QdrantClient + OpenAIEmbeddings implementation.
    """

    async def find_similar(self, logs: str, threshold: float = 0.92) -> dict | None:
        return None

    async def store(self, logs: str, analysis: dict) -> None:
        return None
```

### Orchestrator wiring (`src/orchestrator/nodes.py` — modified)

Replace the existing `analyze_crash` stub:

```python
from src.agents.fix_agent import get_fix_agent


async def analyze_crash(state: CrashState) -> dict:
    """Node: call FixAgent to analyze the crash event."""
    agent = get_fix_agent()
    analysis, cache_hit = await agent.analyze(state["crash_event"])
    return {
        "analysis": analysis.model_dump(),
        "cache_hit": cache_hit,
    }
```

## Error handling

| Failure | Where | Response |
|---|---|---|
| Missing `OPENAI_API_KEY` | First call to LLM | `ChatOpenAI` raises; caught in `analyze`'s try/except → minimal fallback. |
| OpenAI rate limit on primary | `chain.ainvoke` | LangChain falls back to gpt-4o automatically. No code. |
| Both primary + fallback fail | `chain.ainvoke` | Caught in `analyze`, minimal fallback returned. `log_event` runs. |
| Malformed structured output | LangChain validation | Raises → same path as other failures → minimal fallback. |
| Prompt too long | Shouldn't happen | Log truncation keeps prompt well under gpt-4o-mini's 128K window. |
| CrashMemory.find_similar raises | — | Phase 2 stub returns None cleanly. Phase 3 adds real error handling. |
| CrashMemory.store raises | After analysis succeeds | Caught locally, logged, call returns analysis anyway. Cache is best-effort. |

## Logging

Logger: `sentinel.agents.fix`. Levels:
- `INFO` on successful analysis.
- `WARNING` on primary→fallback transition (LangChain doesn't always expose this cleanly — best-effort).
- `ERROR` on both-fail via `logger.exception`.

No Prometheus metrics this session. Add in Phase 3 / Observability work.

## Testing

### Unit tests

**`tests/unit/agents/test_prompt_builder.py`** — pure function, no mocks:
- Contains container_name, image, exit_code, event_type, logs.
- Truncates logs beyond 200 lines (keeps last 200).
- Handles missing logs (`None` → "<no logs captured>").
- Handles missing container_name and image (→ `<unknown>`).
- Returns proper message-list shape.

**`tests/unit/agents/test_fix_agent.py`** — LLM + memory mocked:
- `test_analyze_cache_hit_returns_cached_and_skips_llm`
- `test_analyze_cache_miss_calls_llm_and_stores`
- `test_analyze_llm_failure_returns_minimal_fallback`
- `test_analyze_llm_failure_skips_store`
- `test_get_fix_agent_returns_singleton`

**`tests/unit/orchestrator/test_analyze_crash.py`** — rewrite existing tests:
- Remove the 2 stub-era tests.
- Add `test_analyze_crash_calls_fix_agent_and_returns_analysis` (mocks `get_fix_agent`).
- Add `test_analyze_crash_propagates_cache_hit`.

**`tests/unit/orchestrator/test_workflow_end_to_end.py`** — update:
- Add a `patch("src.orchestrator.nodes.get_fix_agent")` block so the E2E test doesn't try to instantiate a real OpenAI client.

### No real-OpenAI tests

CI runs with no API key; unit tests never call the real API. Manual verification happens in the smoke-test task.

### Expected counts

- +5 prompt builder tests
- +5 FixAgent tests
- +2 analyze_crash tests (replacing 2 stubbed tests — net 0)
- E2E test updated (no net new test)

Current suite: 46 tests. After this session: ~56 tests.

## Dependencies

No new Python packages. Existing `langchain-openai>=0.3.0` covers the scope.

Environment: `OPENAI_API_KEY` must be set at worker startup. User confirmed it is already in `.env`.

## Acceptance criteria

1. Real crash event routed through the workflow produces a `CrashEvent` row with populated `root_cause`, `severity`, `category`, `suggestions` — LLM-generated, not canned.
2. Simulating an LLM failure (invalid API key or blocked network) produces a row with `confidence=0.0`; workflow still completes.
3. All unit tests pass with mocked LLM; no real OpenAI calls in CI.
4. `analyze_crash` node propagates `cache_hit` — always `False` today until Phase 3 Qdrant lands.
5. `CrashMemory` methods no longer raise `NotImplementedError` (they return None / pass).
