# Orchestrator Nodes (Phase 1 finish) — Design

**Date:** 2026-04-21
**Scope:** Phase 1 items #4, #5, #6 from `work-tracking/PROGRESS.md` — the three LangGraph orchestrator nodes that turn a delivered crash event into a completed `CrashEvent` row.

- `analyze_crash` — stubbed in this session (real Fix Agent in Phase 2)
- `attempt_restart` — pure Docker SDK, no LLM
- `log_event` — terminal node, persists workflow state to the existing `CrashEvent` row

Out of scope: `notify_slack`, `send_email`, `make_call`. They remain `NotImplementedError` and are unreachable on the stubbed happy path.

## Goals

1. The full `crash_workflow` runs to completion today without any `NotImplementedError` on the happy path.
2. An end-to-end crash produces a `CrashEvent` row with `restart_attempted`, `restart_success`, and `resolved_at` populated.
3. When Fix Agent lands (Phase 2), only the body of `analyze_crash` changes — no schema or graph edits.

## Non-goals

- Fix Agent, Qdrant cache, embeddings, prompt engineering.
- Slack/email/call notification implementations.
- Retries, dead-letter handling, or sophisticated error recovery.
- Multi-crash detection logic (`recent_crash_count` stays `0`).

## Architecture

```
  Redis event → worker._process_event inserts pending CrashEvent row
                            ↓
               build initial CrashState with crash_event_id
                            ↓
                   crash_workflow.ainvoke(state)
                            ↓
                    ┌──────────────┐
                    │ analyze_crash│  stub today — returns canned CrashAnalysis
                    └──────┬───────┘  (restart_likely_fixes=True, severity=medium)
                           ↓
                    should_restart? (existing conditional edge)
                           ↓ restart_likely_fixes=True
                    ┌──────────────┐
                    │attempt_restart│  fresh Docker client, container.restart()
                    └──────┬───────┘  → restart_success: True | False
                           ↓
                    check_restart_result? (existing)
                     ↓ success=True            ↓ success=False
                  log_event                  notify_slack (NotImplementedError)
                     ↓                       (unreachable via stub today)
                    END
```

Stubbed `analyze_crash` forces traffic through `attempt_restart → log_event`, the two paths built in this session.

## Key design decisions

### `analyze_crash` is a stub, not a deferred feature

Body returns a canned `CrashAnalysis` dict with `restart_likely_fixes=True`. This is the minimum needed to keep the state machine live. When Fix Agent is ready (next session), we swap the body — signature, return shape, and node identity stay the same.

**Why:** Incremental shipping. The deterministic half of Phase 1 is independently valuable (restart orchestration, DB lifecycle) and avoids coupling this session to Anthropic API setup.

### `attempt_restart` is stateless — builds its own Docker client

The orchestrator does not reach into `ListenerManager._listeners` to reuse a connection. It queries `DockerHost` from the DB, builds a fresh client, performs the restart, and closes the client.

**Why:** Two separately testable, independently deployable surfaces. Listener and orchestrator talk only via Redis + DB. The ~50ms client-construction cost is negligible next to future LLM calls.

### `log_event` is idempotent UPDATE, not INSERT

`_process_event` (worker) already inserts a pending `CrashEvent` row before invoking the workflow. `log_event` UPDATES that row. `resolved_at = now()` unconditionally on every run.

**Why:** The row already exists. Creating a second row would break analytics queries. `resolved_at` meaning "workflow completed" is cleaner than "problem fixed" — we can refine later if needed.

### TLS config helper is extracted

`ListenerManager._build_tls_config` is lifted into `src/listener/_tls.py` so both the manager (spawning monitors) and `attempt_restart` (building ad-hoc clients) import the same logic. Small refactor, fits the existing `_dedup.py` / `_filter.py` / `_status.py` pattern in `src/listener/`.

## Component specifications

### State schema (`src/orchestrator/state.py`)

```python
class CrashState(TypedDict):
    # Input — set by worker._process_event
    tenant_id: str
    crash_event_id: str
    docker_host_id: str
    crash_event: dict

    # Populated by analyze_crash (stub today, Fix Agent later)
    analysis: dict | None
    cache_hit: bool

    # Populated by attempt_restart
    restart_attempted: bool
    restart_success: bool | None

    # Populated by notification nodes (NotImplementedError for Phase 1)
    slack_sent: bool
    email_sent: bool
    call_triggered: bool

    # Stretch — 0 for now
    recent_crash_count: int
```

Initial values built in `_process_event`:

```python
state = {
    "tenant_id": str(tenant_id),
    "crash_event_id": str(crash_row.id),
    "docker_host_id": event["docker_host_id"],
    "crash_event": event,
    "analysis": None,
    "cache_hit": False,
    "restart_attempted": False,
    "restart_success": None,
    "slack_sent": False,
    "email_sent": False,
    "call_triggered": False,
    "recent_crash_count": 0,
}
```

### `analyze_crash` (stub)

```python
async def analyze_crash(state: CrashState) -> dict:
    return {
        "analysis": {
            "restart_likely_fixes": True,
            "root_cause": "Pending Fix Agent implementation (Phase 2)",
            "severity": "medium",
            "category": "unknown",
            "suggestions": ["Fix Agent not yet implemented — placeholder analysis"],
            "confidence": 0.0,
        },
        "cache_hit": False,
    }
```

### `attempt_restart`

```python
async def attempt_restart(state: CrashState) -> dict:
    host_id = uuid.UUID(state["docker_host_id"])
    container_id = state["crash_event"]["container_id"]

    async with async_session_factory() as session:
        host = await session.get(DockerHost, host_id)

    if host is None:
        logger.warning("Docker host %s not found; cannot restart", host_id)
        return {"restart_attempted": True, "restart_success": False}

    tls_config = build_tls_config(host)

    def _do_restart() -> bool:
        client = docker.DockerClient(base_url=host.tcp_url, tls=tls_config)
        try:
            container = client.containers.get(container_id)
            container.restart(timeout=10)
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError:
            logger.exception("Restart failed for container %s", container_id)
            return False
        finally:
            try:
                client.close()
            except Exception:
                pass

    success = await asyncio.to_thread(_do_restart)
    return {"restart_attempted": True, "restart_success": success}
```

### `log_event`

```python
async def log_event(state: CrashState) -> dict:
    crash_id = uuid.UUID(state["crash_event_id"])
    analysis = state.get("analysis") or {}

    async with async_session_factory() as session:
        await session.execute(
            update(CrashEvent)
            .where(CrashEvent.id == crash_id)
            .values(
                root_cause=analysis.get("root_cause"),
                category=analysis.get("category"),
                severity=analysis.get("severity"),
                confidence=analysis.get("confidence"),
                suggestions=analysis.get("suggestions") or [],
                restart_attempted=state.get("restart_attempted", False),
                restart_success=state.get("restart_success"),
                cache_hit=state.get("cache_hit", False),
                slack_sent=state.get("slack_sent", False),
                email_sent=state.get("email_sent", False),
                call_made=state.get("call_triggered", False),
                resolved_at=func.now(),
            )
        )
        await session.commit()
    return {}
```

### TLS helper extraction (`src/listener/_tls.py`)

```python
import tempfile
import docker

from src.models.docker_host import DockerHost


def build_tls_config(host: DockerHost):
    """Build a docker.tls.TLSConfig from PEM strings stored in the DB.

    Returns None if TLS is not enabled. Writes certs to temp files; caller
    must accept that cleanup is deferred until process exit.
    """
    if not host.tls_enabled:
        return None

    def _write(pem: str) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", mode="w")
        f.write(pem)
        f.close()
        return f.name

    return docker.tls.TLSConfig(
        ca_cert=_write(host.tls_ca) if host.tls_ca else None,
        client_cert=(
            (_write(host.tls_cert), _write(host.tls_key))
            if host.tls_cert and host.tls_key
            else None
        ),
        verify=True,
    )
```

`ListenerManager._build_tls_config` is replaced by a delegation to this helper.

### Worker update (`src/worker/main.py::_process_event`)

The existing state-building block:

```python
state = {
    "crash_event_id": str(crash_event_id),
    "tenant_id": str(tenant_id),
    "event_data": event,
}
```

becomes:

```python
state = {
    "tenant_id": str(tenant_id),
    "crash_event_id": str(crash_event_id),
    "docker_host_id": event["docker_host_id"],
    "crash_event": event,
    "analysis": None,
    "cache_hit": False,
    "restart_attempted": False,
    "restart_success": None,
    "slack_sent": False,
    "email_sent": False,
    "call_triggered": False,
    "recent_crash_count": 0,
}
```

## Error handling

| Node | Failure | Response |
|---|---|---|
| `analyze_crash` | N/A — pure stub | — |
| `attempt_restart` | `DockerHost` row missing | `restart_success=False`, logged. Graph continues. |
| `attempt_restart` | Docker daemon unreachable | `APIError` caught, `restart_success=False`, logged. |
| `attempt_restart` | Container auto-removed (`--rm`) | `NotFound` caught, `restart_success=False`. Legitimate outcome. |
| `attempt_restart` | TLS cert invalid | `TLSParameterError` → `APIError` path, `restart_success=False`. |
| `log_event` | Row missing (should not happen) | `UPDATE` affects 0 rows; node no-ops without exception. |
| `log_event` | DB unreachable | `SQLAlchemyError` propagates to the worker's `_process_event` exception handler. Logged, event acked. |
| Workflow overall | Any exception | Caught in `_process_event`, logged, event acked. No retry, no DLQ. |

## Testing

### Unit tests (`tests/unit/orchestrator/`)

- `test_analyze_crash.py` — trivial: invoke stub, assert returned `analysis` dict has the expected shape and `cache_hit=False`.
- `test_attempt_restart.py` — three scenarios (patch `docker.DockerClient`, patch `async_session_factory`):
  - Happy path: mock `container.restart()` returns, assert `restart_success=True`.
  - Container `NotFound`: assert `restart_success=False`, no exception.
  - Host row missing: assert `restart_success=False`, Docker client never constructed.
- `test_log_event.py` — two scenarios:
  - Happy path with full state: assert UPDATE includes all analysis + action fields.
  - Empty `analysis` (None): assert UPDATE runs with NULL/default values.

### Integration test (`tests/integration/orchestrator/test_workflow.py`)

One end-to-end run:
- Seed a real Postgres `tenants` + `docker_hosts` + pending `crash_events` row.
- Mock `docker.DockerClient` to simulate successful restart.
- Build `CrashState` and call `crash_workflow.ainvoke(state)`.
- Assert the `crash_events` row has `restart_attempted=True`, `restart_success=True`, `root_cause`, `resolved_at` populated.

### Worker test update (`tests/unit/worker/test_process_event.py`)

Extend existing tests: assert the new state shape (`crash_event`, `docker_host_id`, `crash_event_id` all present).

### Expected totals

- +8 unit tests (orchestrator nodes)
- +1 integration test
- Extended worker test (no new count)

Current suite = 32 tests. After this session: ~41 tests.

## Dependencies

No new Python packages. Existing imports (`docker`, `sqlalchemy`, `langgraph`) already cover the scope.

## Acceptance criteria

Phase 1 items #4, #5, #6 are done when:

1. `crash_workflow.ainvoke()` completes without `NotImplementedError` on the happy path.
2. A smoke-test crash produces a fully populated `CrashEvent` row (analysis + action fields + `resolved_at`).
3. Killing a container whose `DockerHost` is active results in `restart_attempted=True` + `restart_success=True` in the DB.
4. All unit and integration tests pass.
5. Worker's state-building in `_process_event` matches the new `CrashState` schema.
