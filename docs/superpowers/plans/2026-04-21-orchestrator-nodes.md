# Orchestrator Nodes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish Phase 1 items #4–6 — implement `log_event`, `attempt_restart`, and a stubbed `analyze_crash` so the LangGraph `crash_workflow` runs end-to-end without `NotImplementedError` on the happy path.

**Architecture:** Three async node functions in `src/orchestrator/nodes.py`. `analyze_crash` returns canned analysis (Fix Agent replaces the body in Phase 2). `attempt_restart` builds a fresh Docker client stateless-per-invocation and calls `container.restart()`. `log_event` updates the existing pending `CrashEvent` row with all analysis + action results. State schema is updated to carry `crash_event_id` and `docker_host_id`; worker's `_process_event` is updated to match.

**Tech Stack:** Python 3.11, LangGraph, Docker SDK, SQLAlchemy async, pytest + pytest-asyncio.

**Spec reference:** `docs/superpowers/specs/2026-04-21-orchestrator-nodes-design.md`

---

## File Structure

### Files to modify
- `src/orchestrator/state.py` — new `CrashState` fields (`crash_event_id`, `docker_host_id`; make `restart_success` nullable).
- `src/orchestrator/nodes.py` — replace `analyze_crash`, `attempt_restart`, `log_event` stubs with real bodies. Leave notification nodes untouched.
- `src/worker/main.py` — update `_process_event` state-building block to match new schema.
- `src/listener/manager.py` — replace inline `_build_tls_config` method body with a call to the new shared helper.
- `tests/unit/worker/test_process_event.py` — update test assertions for the new state shape.
- `work-tracking/PROGRESS.md` — mark Phase 1 items #4, #5, #6 complete; add daily log entry.

### New files
- `src/listener/_tls.py` — extracted `build_tls_config(host)` helper.
- `tests/unit/orchestrator/__init__.py`
- `tests/unit/orchestrator/conftest.py` — shared fixtures (DB factory, docker client mock).
- `tests/unit/orchestrator/test_analyze_crash.py`
- `tests/unit/orchestrator/test_attempt_restart.py`
- `tests/unit/orchestrator/test_log_event.py`

### Responsibilities per file
- `state.py` — the TypedDict that flows through the graph. Shape-only, no logic.
- `nodes.py` — async node functions. Each returns a partial-state dict; LangGraph merges.
- `_tls.py` — one pure function that builds a `docker.tls.TLSConfig` from a `DockerHost` row.
- `manager.py` (modified) — already owns monitor lifecycle; TLS concern now delegated.

---

## Task 1: Extract TLS config helper

**Files:**
- Create: `src/listener/_tls.py`
- Modify: `src/listener/manager.py`

Pure refactor. No behavior change. Existing `ListenerManager` tests must still pass without modification.

- [ ] **Step 1: Create the helper**

Create `src/listener/_tls.py`:

```python
import tempfile

import docker

from src.models.docker_host import DockerHost


def build_tls_config(host: DockerHost):
    """Build a docker.tls.TLSConfig from PEM strings stored in the DB row.

    Returns None if TLS is not enabled. Writes certs to tempfiles that are
    not cleaned up (acceptable at portfolio scale; production would manage
    tempfile lifetimes explicitly).
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

- [ ] **Step 2: Update `ListenerManager` to delegate**

In `src/listener/manager.py`, replace the `_build_tls_config` method (and remove the inline `import tempfile` inside it) with a delegation to the shared helper.

Add to the imports at the top:

```python
from src.listener._tls import build_tls_config
```

Replace the existing `_build_tls_config` method with:

```python
    def _build_tls_config(self, host: DockerHost):
        return build_tls_config(host)
```

- [ ] **Step 3: Run the existing listener tests — verify no regressions**

Run: `py -3.12 -m pytest tests/unit/listener/ -v`
Expected: 23 tests pass, same as before.

- [ ] **Step 4: Commit**

```bash
git add src/listener/_tls.py src/listener/manager.py
git commit -m "refactor(listener): extract TLS config builder to _tls.py"
```

---

## Task 2: Update `CrashState` schema

**Files:**
- Modify: `src/orchestrator/state.py`

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `src/orchestrator/state.py`:

```python
from typing import TypedDict


class CrashState(TypedDict):
    """State that flows through the LangGraph orchestrator."""

    # Input — set by worker._process_event before invocation
    tenant_id: str
    crash_event_id: str
    docker_host_id: str
    crash_event: dict

    # Populated by analyze_crash (stub today, Fix Agent in Phase 2)
    analysis: dict | None
    cache_hit: bool

    # Populated by attempt_restart
    restart_attempted: bool
    restart_success: bool | None

    # Populated by notification nodes (NotImplementedError for Phase 1)
    slack_sent: bool
    email_sent: bool
    call_triggered: bool

    # Stretch — 0 for Phase 1
    recent_crash_count: int
```

- [ ] **Step 2: Verify the orchestrator module still imports**

Run: `py -3.12 -c "from src.orchestrator.state import CrashState; from src.orchestrator.graph import crash_workflow; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Run the full unit-test suite — no regressions**

Run: `py -3.12 -m pytest tests/unit/ -v`
Expected: 30 tests pass (state schema is structural, no tests target it directly).

- [ ] **Step 4: Commit**

```bash
git add src/orchestrator/state.py
git commit -m "feat(orchestrator): update CrashState with crash_event_id and docker_host_id"
```

---

## Task 3: Update worker `_process_event` for new state shape

**Files:**
- Modify: `src/worker/main.py`
- Modify: `tests/unit/worker/test_process_event.py`

- [ ] **Step 1: Update the failing test first (TDD)**

In `tests/unit/worker/test_process_event.py`, replace the `test_process_event_invokes_langgraph_workflow` test with:

```python
@pytest.mark.asyncio
async def test_process_event_invokes_langgraph_workflow(tenant_id, event_payload, mock_session_factory):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock()
        await _process_event(event_payload, tenant_id, mock_session_factory)
        wf.ainvoke.assert_awaited_once()
        state = wf.ainvoke.await_args.args[0]
        assert state["tenant_id"] == str(tenant_id)
        assert "crash_event_id" in state
        assert state["docker_host_id"] == event_payload["docker_host_id"]
        assert state["crash_event"] == event_payload
        assert state["analysis"] is None
        assert state["cache_hit"] is False
        assert state["restart_attempted"] is False
        assert state["restart_success"] is None
        assert state["slack_sent"] is False
        assert state["email_sent"] is False
        assert state["call_triggered"] is False
        assert state["recent_crash_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/unit/worker/test_process_event.py::test_process_event_invokes_langgraph_workflow -v`
Expected: FAIL — `state["docker_host_id"]` missing, `state["crash_event"]` missing.

- [ ] **Step 3: Update `_process_event` in `src/worker/main.py`**

Find the `state = {...}` block inside `_process_event` and replace it with:

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/worker/ -v`
Expected: all 7 worker tests pass.

Also run: `py -3.12 -m pytest tests/unit/ -v`
Expected: 30 tests pass (no new tests, same as before).

- [ ] **Step 5: Commit**

```bash
git add src/worker/main.py tests/unit/worker/test_process_event.py
git commit -m "feat(worker): update _process_event to build full CrashState shape"
```

---

## Task 4: Scaffold orchestrator tests directory

**Files:**
- Create: `tests/unit/orchestrator/__init__.py`
- Create: `tests/unit/orchestrator/conftest.py`

- [ ] **Step 1: Create the `__init__.py`**

Create `tests/unit/orchestrator/__init__.py` with one line: `# test package`.

- [ ] **Step 2: Create shared fixtures**

Create `tests/unit/orchestrator/conftest.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def tenant_id():
    return uuid.UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture
def host_id():
    return uuid.UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture
def crash_event_id():
    return uuid.UUID("66666666-6666-6666-6666-666666666666")


@pytest.fixture
def crash_event_payload(host_id):
    return {
        "docker_host_id": str(host_id),
        "container_name": "web-1",
        "container_id": "abc123def456",
        "image": "nginx:latest",
        "exit_code": 137,
        "logs": "out of memory",
        "event_type": "die",
        "event_timestamp": "2026-04-21T12:00:00+00:00",
    }


@pytest.fixture
def initial_state(tenant_id, host_id, crash_event_id, crash_event_payload):
    return {
        "tenant_id": str(tenant_id),
        "crash_event_id": str(crash_event_id),
        "docker_host_id": str(host_id),
        "crash_event": crash_event_payload,
        "analysis": None,
        "cache_hit": False,
        "restart_attempted": False,
        "restart_success": None,
        "slack_sent": False,
        "email_sent": False,
        "call_triggered": False,
        "recent_crash_count": 0,
    }


@pytest.fixture
def fake_session_factory():
    """Factory that yields a mock async session supporting add/execute/commit/get."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return MagicMock(return_value=session)
```

- [ ] **Step 3: Verify pytest collects the directory**

Run: `py -3.12 -m pytest tests/unit/orchestrator/ --collect-only`
Expected: No errors, no tests collected yet.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/orchestrator
git commit -m "test: scaffold tests/unit/orchestrator directory with shared fixtures"
```

---

## Task 5: Implement `analyze_crash` stub

**Files:**
- Modify: `src/orchestrator/nodes.py`
- Create: `tests/unit/orchestrator/test_analyze_crash.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/orchestrator/test_analyze_crash.py`:

```python
import pytest

from src.orchestrator.nodes import analyze_crash


@pytest.mark.asyncio
async def test_analyze_crash_returns_canned_analysis(initial_state):
    result = await analyze_crash(initial_state)

    assert "analysis" in result
    assert "cache_hit" in result
    assert result["cache_hit"] is False

    a = result["analysis"]
    assert a["restart_likely_fixes"] is True
    assert a["severity"] == "medium"
    assert a["category"] == "unknown"
    assert a["confidence"] == 0.0
    assert isinstance(a["suggestions"], list)
    assert isinstance(a["root_cause"], str)


@pytest.mark.asyncio
async def test_analyze_crash_does_not_mutate_input_state(initial_state):
    snapshot = dict(initial_state)
    await analyze_crash(initial_state)
    assert initial_state == snapshot
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_analyze_crash.py -v`
Expected: FAIL — `analyze_crash` raises `NotImplementedError`.

- [ ] **Step 3: Replace the `analyze_crash` function body**

In `src/orchestrator/nodes.py`, replace the `analyze_crash` function with:

```python
async def analyze_crash(state: CrashState) -> dict:
    """Node: stub until Fix Agent lands in Phase 2.

    Returns a canned CrashAnalysis dict so the state machine stays live.
    Sets restart_likely_fixes=True to route through attempt_restart → log_event.
    """
    return {
        "analysis": {
            "restart_likely_fixes": True,
            "root_cause": "Pending Fix Agent implementation (Phase 2)",
            "severity": "medium",
            "category": "unknown",
            "suggestions": [
                "Fix Agent not yet implemented — placeholder analysis"
            ],
            "confidence": 0.0,
        },
        "cache_hit": False,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_analyze_crash.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/nodes.py tests/unit/orchestrator/test_analyze_crash.py
git commit -m "feat(orchestrator): add analyze_crash stub with canned CrashAnalysis"
```

---

## Task 6: Implement `attempt_restart`

**Files:**
- Modify: `src/orchestrator/nodes.py`
- Create: `tests/unit/orchestrator/test_attempt_restart.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/orchestrator/test_attempt_restart.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import docker.errors
import pytest

from src.orchestrator.nodes import attempt_restart


def _fake_host(host_id, tls_enabled=False):
    h = MagicMock()
    h.id = host_id
    h.tcp_url = "tcp://test:2376"
    h.tls_enabled = tls_enabled
    h.tls_ca = None
    h.tls_cert = None
    h.tls_key = None
    return h


@pytest.mark.asyncio
async def test_attempt_restart_success(initial_state, host_id):
    fake_host = _fake_host(host_id)
    fake_container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client) as client_ctor:
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": True}
    client_ctor.assert_called_once()
    fake_container.restart.assert_called_once_with(timeout=10)
    fake_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_restart_container_not_found(initial_state, host_id):
    fake_host = _fake_host(host_id)
    fake_client = MagicMock()
    fake_client.containers.get.side_effect = docker.errors.NotFound("gone")

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client):
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": False}
    fake_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_restart_host_missing(initial_state):
    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient") as client_ctor:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": False}
    client_ctor.assert_not_called()


@pytest.mark.asyncio
async def test_attempt_restart_docker_api_error(initial_state, host_id):
    fake_host = _fake_host(host_id)
    fake_client = MagicMock()
    fake_client.containers.get.side_effect = docker.errors.APIError("daemon down")

    with patch("src.orchestrator.nodes.async_session_factory") as factory, \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client):
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_host)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        factory.return_value = session

        result = await attempt_restart(initial_state)

    assert result == {"restart_attempted": True, "restart_success": False}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_attempt_restart.py -v`
Expected: FAIL — `attempt_restart` raises `NotImplementedError`.

- [ ] **Step 3: Replace the `attempt_restart` function body**

In `src/orchestrator/nodes.py`, add these imports at the top if not already present:

```python
import asyncio
import logging
import uuid

import docker
import docker.errors

from src.listener._tls import build_tls_config
from src.models.docker_host import DockerHost
from src.orchestrator.state import CrashState
from src.services.database import async_session_factory

logger = logging.getLogger("sentinel.orchestrator")
```

(Keep any existing imports; add only what is missing. Remove the lone `from src.orchestrator.state import CrashState` if it was the only import.)

Replace the `attempt_restart` function with:

```python
async def attempt_restart(state: CrashState) -> dict:
    """Node: attempt container restart on its Docker host.

    Stateless — builds a fresh Docker client per invocation.
    """
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
            logger.exception(
                "Restart failed for container %s on host %s",
                container_id,
                host_id,
            )
            return False
        finally:
            try:
                client.close()
            except Exception:
                pass

    success = await asyncio.to_thread(_do_restart)
    return {"restart_attempted": True, "restart_success": success}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_attempt_restart.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/nodes.py tests/unit/orchestrator/test_attempt_restart.py
git commit -m "feat(orchestrator): implement attempt_restart with Docker SDK restart"
```

---

## Task 7: Implement `log_event`

**Files:**
- Modify: `src/orchestrator/nodes.py`
- Create: `tests/unit/orchestrator/test_log_event.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/orchestrator/test_log_event.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.nodes import log_event


def _state_with_analysis(base_state, **overrides):
    state = dict(base_state)
    state.update({
        "analysis": {
            "restart_likely_fixes": True,
            "root_cause": "OOM killed",
            "severity": "high",
            "category": "oom",
            "suggestions": ["increase memory limit", "investigate leak"],
            "confidence": 0.85,
        },
        "cache_hit": False,
        "restart_attempted": True,
        "restart_success": True,
        "slack_sent": False,
        "email_sent": False,
        "call_triggered": False,
    })
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_log_event_updates_row_with_full_analysis(initial_state):
    state = _state_with_analysis(initial_state)
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session):
        result = await log_event(state)

    assert result == {}
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()

    # Inspect the UPDATE values passed through sqlalchemy's update().values(...)
    stmt = session.execute.await_args.args[0]
    values = stmt.compile().params
    assert values["root_cause"] == "OOM killed"
    assert values["category"] == "oom"
    assert values["severity"] == "high"
    assert values["confidence"] == 0.85
    assert values["suggestions"] == ["increase memory limit", "investigate leak"]
    assert values["restart_attempted"] is True
    assert values["restart_success"] is True


@pytest.mark.asyncio
async def test_log_event_handles_none_analysis(initial_state):
    state = dict(initial_state)
    state["analysis"] = None
    state["restart_attempted"] = False

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session):
        await log_event(state)

    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    values = stmt.compile().params
    assert values["root_cause"] is None
    assert values["category"] is None
    assert values["suggestions"] == []
    assert values["restart_attempted"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_log_event.py -v`
Expected: FAIL — `log_event` raises `NotImplementedError`.

- [ ] **Step 3: Replace the `log_event` function body**

In `src/orchestrator/nodes.py`, add these imports if not already present:

```python
from sqlalchemy import func, update

from src.models.crash_event import CrashEvent
```

Replace the `log_event` function with:

```python
async def log_event(state: CrashState) -> dict:
    """Node: UPDATE the pending CrashEvent row with analysis + action results.

    Sets resolved_at = now() unconditionally — "workflow completed",
    not "problem fixed".
    """
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_log_event.py -v`
Expected: PASS (2 tests).

Also run the full unit suite:

Run: `py -3.12 -m pytest tests/unit/ -v`
Expected: 38 tests pass (30 previous + 2 analyze + 4 restart + 2 log).

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/nodes.py tests/unit/orchestrator/test_log_event.py
git commit -m "feat(orchestrator): implement log_event to persist workflow state"
```

---

## Task 8: End-to-end workflow integration test

**Files:**
- Create: `tests/unit/orchestrator/test_workflow_end_to_end.py`

This runs the compiled `crash_workflow` with mocked Docker + DB to confirm the three nodes compose correctly via LangGraph's conditional edges. Placed under `tests/unit/` (not a real integration test — no real DB or Docker), since it can run fast without external dependencies.

- [ ] **Step 1: Write the end-to-end test**

Create `tests/unit/orchestrator/test_workflow_end_to_end.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.graph import crash_workflow


def _fake_host(host_id):
    h = MagicMock()
    h.id = host_id
    h.tcp_url = "tcp://test:2376"
    h.tls_enabled = False
    h.tls_ca = None
    h.tls_cert = None
    h.tls_key = None
    return h


@pytest.mark.asyncio
async def test_workflow_happy_path_invokes_all_three_nodes(initial_state, host_id):
    """analyze_crash (stub) → attempt_restart (success) → log_event.

    Asserts that the compiled workflow threads state correctly via LangGraph's
    conditional edges and that the terminal log_event node runs.
    """
    fake_host = _fake_host(host_id)
    fake_container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.get.return_value = fake_container

    session = AsyncMock()
    session.get = AsyncMock(return_value=fake_host)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session), \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_client):
        final_state = await crash_workflow.ainvoke(initial_state)

    # analyze_crash stub ran
    assert final_state["analysis"] is not None
    assert final_state["analysis"]["restart_likely_fixes"] is True
    assert final_state["cache_hit"] is False

    # attempt_restart ran and succeeded
    assert final_state["restart_attempted"] is True
    assert final_state["restart_success"] is True
    fake_container.restart.assert_called_once_with(timeout=10)

    # log_event ran (UPDATE executed on the CrashEvent row)
    # session.execute was called at least twice — once in attempt_restart (get host)
    # and once in log_event (UPDATE). The UPDATE is the one we care about:
    update_calls = [c for c in session.execute.await_args_list]
    assert len(update_calls) >= 1
    # session.commit was awaited by log_event
    session.commit.assert_awaited()
```

- [ ] **Step 2: Run the test**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_workflow_end_to_end.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Run the entire test suite — full green**

Run: `py -3.12 -m pytest tests/unit/ tests/test_services/test_crash_event_schema.py -v`
Expected: 41 tests pass (30 baseline + 9 new in this session; includes 2 crash_event_schema from Phase 1).

- [ ] **Step 4: Commit**

```bash
git add tests/unit/orchestrator/test_workflow_end_to_end.py
git commit -m "test(orchestrator): add end-to-end workflow test through all three nodes"
```

---

## Task 9: Update work tracker

**Files:**
- Modify: `work-tracking/PROGRESS.md`

- [ ] **Step 1: Mark Phase 1 items 4–6 done**

In `work-tracking/PROGRESS.md`, under the Phase 1 table, change the priority of items 4, 5, 6 from `**Critical**` to `✅ **Done**`. For item 4, append a note that it is stubbed:

Find this block:

```markdown
| 4 | `src/orchestrator/nodes.py` → `analyze_crash` | Fix Agent call (Qdrant cache check + LLM analysis) | **Critical** |
| 5 | `src/orchestrator/nodes.py` → `attempt_restart` | Docker SDK restart container | **Critical** |
| 6 | `src/orchestrator/nodes.py` → `log_event` | Persist crash event result to PostgreSQL | **Critical** |
```

Replace with:

```markdown
| 4 | `src/orchestrator/nodes.py` → `analyze_crash` | Fix Agent call (Qdrant cache check + LLM analysis) | ✅ **Stubbed** (body filled in by Phase 2 Fix Agent) |
| 5 | `src/orchestrator/nodes.py` → `attempt_restart` | Docker SDK restart container | ✅ **Done** |
| 6 | `src/orchestrator/nodes.py` → `log_event` | Persist crash event result to PostgreSQL | ✅ **Done** |
```

- [ ] **Step 2: Add today's daily log entry**

Under the `## Daily Log` heading, insert this new entry after the existing `### 2026-04-21 (Today)` entry:

```markdown
### 2026-04-21 (Continued — afternoon session)
- **Status:** ✅ **Phase 1 items #5 and #6 shipped**; #4 stubbed (Fix Agent replaces body in Phase 2).
- **What was done:**
  - Extracted TLS config helper to `src/listener/_tls.py`; `ListenerManager` delegates.
  - Updated `CrashState` schema: added `crash_event_id`, `docker_host_id`; made `restart_success` nullable.
  - Updated `worker._process_event` to build the full state dict.
  - Stubbed `analyze_crash` (returns canned CrashAnalysis with `restart_likely_fixes=True`).
  - Implemented `attempt_restart` (stateless fresh Docker client per invocation, handles NotFound + APIError).
  - Implemented `log_event` (UPDATE pending CrashEvent row with all analysis + action fields, `resolved_at = now()`).
  - Added ~10 unit tests (orchestrator nodes + end-to-end workflow test). Total suite: ~41 tests.
  - Design: `docs/superpowers/specs/2026-04-21-orchestrator-nodes-design.md`
  - Plan: `docs/superpowers/plans/2026-04-21-orchestrator-nodes.md`
- **Pick up from here:** **Phase 2 Fix Agent** (item #7) — replace the `analyze_crash` stub body with real Claude Haiku calls. Then Qdrant cache (items #15, #16) to deduplicate semantically-similar crashes. After Fix Agent: notification agents (items #8–11).
```

- [ ] **Step 3: Commit**

```bash
git add work-tracking/PROGRESS.md
git commit -m "docs: mark Phase 1 items 4-6 complete in work tracker"
```

---

## Task 10: Smoke test re-run

**Files:** none — verification only.

Reuse yesterday's smoke-test scaffolding (`scripts/smoke_seed.py`, compose stack). This time the expectation changes: the worker no longer logs "LangGraph node not implemented" — instead, crashes produce fully-populated `CrashEvent` rows.

- [ ] **Step 1: Start infra + run migrations**

Run (requires Docker Desktop running):

```bash
docker compose up -d postgres redis
py -3.12 -m alembic upgrade head
```

Expected: postgres + redis containers up and healthy; migration runs cleanly.

- [ ] **Step 2: Seed a tenant + host**

Run: `PYTHONPATH=. py -3.12 scripts/smoke_seed.py`
Expected: prints `TENANT_ID=...` and `HOST_ID=...`. Note the tenant UUID.

- [ ] **Step 3: Start the worker in the background**

Run (using Claude's background-task feature or a separate shell): `PYTHONPATH=. py -3.12 -u -m src.worker.main`
Expected: logs show `Starting DockerSentinel worker`, `Spawning listener for host <id>`, `Started DockerMonitor`, host `status` in DB transitions to `connected`.

- [ ] **Step 4: Trigger a crash**

Run: `docker run --name smoke-crash-2 busybox sh -c 'exit 1'`
Expected: container exits with code 1.

- [ ] **Step 5: Verify the Redis stream**

Run: `docker compose exec -T redis redis-cli XLEN crashes:<TENANT_ID>`
Expected: at least 1 (may be more if other containers on the host are also dying).

- [ ] **Step 6: Verify the worker processed the event**

Watch the worker log (stdout or log file). Expected lines in order:
- `Published crash event host=... container=smoke-crash-2 event=die` (from listener)
- No more `"LangGraph node not implemented yet"` — instead, the workflow runs silently to completion

Check the DB:

```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "SELECT container_name, restart_attempted, restart_success, root_cause, resolved_at FROM crash_events WHERE container_name='smoke-crash-2';"
```

Expected: row with `restart_attempted=t`, `restart_success=f` (busybox `--rm` removed it before restart could succeed — legitimate outcome; or `t` if it's slow enough; OR row exists with `resolved_at` NOT NULL either way).

- [ ] **Step 7: Tear down**

Run:

```bash
taskkill //F //IM python.exe    # or Ctrl+C if running in a visible shell
docker rm -f smoke-crash-2 2>/dev/null
docker compose down
```

- [ ] **Step 8: If smoke test confirms end-to-end success, no commit is needed.**

This task is verification only. If something broke, file a follow-up instead of monkey-patching the plan.

---

## Self-review (completed by the planner)

- **Spec coverage:**
  - `analyze_crash` stub → Task 5.
  - `attempt_restart` → Task 6 (happy path + NotFound + host missing + APIError).
  - `log_event` → Task 7 (full analysis + None analysis).
  - State schema → Task 2.
  - Worker update → Task 3 (test updated TDD-style).
  - TLS helper extraction → Task 1.
  - End-to-end test → Task 8.
  - Work tracker → Task 9.
  - Smoke test → Task 10.
- **Placeholder scan:** No TBD, no vague steps. Every code step has full code.
- **Type/name consistency:** `build_tls_config` (snake_case, module-level function) used consistently in Task 1 and Task 6. `crash_event_id` / `docker_host_id` keys consistent across state schema (Task 2), worker (Task 3), fixtures (Task 4), node implementations (Tasks 6, 7), and end-to-end test (Task 8). `restart_success` typed `bool | None` everywhere.
- **Known trade-off flagged (not a placeholder):** The end-to-end test in Task 8 lives under `tests/unit/` despite running the full compiled workflow — acceptable because Docker + DB are mocked. A future real-DB integration test can be added when Phase 2 work introduces non-trivial external dependencies.
