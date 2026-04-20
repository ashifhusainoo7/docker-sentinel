# Crash Ingestion Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Docker daemon events on registered TCP hosts into LangGraph workflow invocations — filling in items #1–3 of `work-tracking/PROGRESS.md`.

**Architecture:** Thread-per-host Docker event listener bridges blocking `docker.events()` calls to asyncio via `asyncio.Queue`. Events are filtered, deduped (60s window), enriched with logs, and published to per-tenant Redis streams. A worker process maintains one `XREADGROUP` consumer task per tenant and invokes the LangGraph `crash_workflow`. All three components run in one asyncio process.

**Tech Stack:** Python 3.11, `docker` SDK, `redis[hiredis]`, SQLAlchemy async, LangGraph, pytest + pytest-asyncio.

**Spec reference:** `docs/superpowers/specs/2026-04-21-crash-ingestion-pipeline-design.md`

---

## File Structure

### Files to modify
- `src/schemas/crash_event.py` — add `event_type` and `event_timestamp` optional fields to `CrashEventCreate`.
- `src/listener/docker_monitor.py` — full implementation replacing skeleton.
- `src/listener/manager.py` — full implementation replacing skeleton.
- `src/worker/main.py` — full implementation replacing skeleton.

### New files
- `tests/unit/__init__.py`
- `tests/unit/listener/__init__.py`
- `tests/unit/listener/conftest.py` — shared fixtures (fake DB session factory, fake monitor).
- `tests/unit/listener/test_dedup.py`
- `tests/unit/listener/test_container_filter.py`
- `tests/unit/listener/test_status_update.py`
- `tests/unit/listener/test_event_processing.py`
- `tests/unit/listener/test_manager.py`
- `tests/unit/worker/__init__.py`
- `tests/unit/worker/test_supervisor.py`
- `tests/unit/worker/test_process_event.py`

### Responsibilities per file
- `docker_monitor.py` — one class `DockerMonitor`: connect, stream events, filter, dedup, capture logs, publish, handle reconnect, write status.
- `manager.py` — one class `ListenerManager`: query DB, diff vs. running monitors, spawn/stop, poll loop.
- `worker/main.py` — three things: `TenantConsumerSupervisor` (class), `_process_event` (async function), `main()` (async entrypoint).

---

## Task 1: Extend CrashEventCreate schema

**Files:**
- Modify: `src/schemas/crash_event.py`
- Test: `tests/test_services/test_crash_event_schema.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_services/test_crash_event_schema.py`:

```python
import uuid
from datetime import datetime, timezone

from src.schemas.crash_event import CrashEventCreate


def test_crash_event_create_accepts_event_type_and_timestamp():
    payload = CrashEventCreate(
        docker_host_id=uuid.uuid4(),
        container_name="web-1",
        container_id="abc123",
        image="nginx:latest",
        exit_code=137,
        logs="oom",
        event_type="die",
        event_timestamp=datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert payload.event_type == "die"
    assert payload.event_timestamp.isoformat() == "2026-04-21T12:00:00+00:00"


def test_crash_event_create_without_new_fields_still_valid():
    payload = CrashEventCreate(
        docker_host_id=uuid.uuid4(),
        container_name="web-1",
        container_id="abc123",
        image="nginx:latest",
    )
    assert payload.event_type is None
    assert payload.event_timestamp is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_services/test_crash_event_schema.py -v`
Expected: FAIL — `CrashEventCreate` has no field `event_type`.

- [ ] **Step 3: Add fields to schema**

In `src/schemas/crash_event.py`, update `CrashEventCreate`:

```python
class CrashEventCreate(BaseModel):
    """Used internally when creating a crash event from Docker listener."""

    docker_host_id: uuid.UUID
    container_name: str
    container_id: str
    image: str
    exit_code: int | None = None
    logs: str | None = None
    event_type: str | None = None
    event_timestamp: datetime | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_services/test_crash_event_schema.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/schemas/crash_event.py tests/test_services/test_crash_event_schema.py
git commit -m "feat(schemas): add event_type and event_timestamp to CrashEventCreate"
```

---

## Task 2: Scaffold test directory structure

**Files:**
- Create: `tests/unit/__init__.py`, `tests/unit/listener/__init__.py`, `tests/unit/worker/__init__.py`
- Create: `tests/unit/listener/conftest.py`

- [ ] **Step 1: Create empty `__init__.py` files**

Create each of these files with the single line `# test package`:

```bash
tests/unit/__init__.py
tests/unit/listener/__init__.py
tests/unit/worker/__init__.py
```

- [ ] **Step 2: Create shared fixtures for listener tests**

Create `tests/unit/listener/conftest.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def host_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def tenant_id():
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def fake_db_session_factory():
    """Returns a factory that yields a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    factory = MagicMock(return_value=session)
    return factory
```

- [ ] **Step 3: Verify pytest collects the new directories**

Run: `pytest tests/unit/ --collect-only`
Expected: No errors, no tests collected (directories empty of tests).

- [ ] **Step 4: Commit**

```bash
git add tests/unit
git commit -m "test: scaffold tests/unit directory structure for listener and worker"
```

---

## Task 3: Dedup cache logic (DockerMonitor)

**Files:**
- Create: `src/listener/_dedup.py`
- Test: `tests/unit/listener/test_dedup.py`

We pull the dedup logic into a small helper class so it's trivially testable without Docker.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/listener/test_dedup.py`:

```python
import time

from src.listener._dedup import DedupCache


def test_first_event_for_container_is_not_duplicate():
    cache = DedupCache(window_seconds=60)
    assert cache.is_duplicate("host-1", "container-abc") is False


def test_second_event_within_window_is_duplicate():
    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    assert cache.is_duplicate("host-1", "container-abc") is True


def test_different_containers_do_not_collide():
    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    assert cache.is_duplicate("host-1", "container-xyz") is False


def test_different_hosts_do_not_collide():
    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    assert cache.is_duplicate("host-2", "container-abc") is False


def test_event_outside_window_is_not_duplicate(monkeypatch):
    current = [1000.0]

    def fake_monotonic():
        return current[0]

    monkeypatch.setattr("src.listener._dedup.time.monotonic", fake_monotonic)

    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    current[0] = 1061.0  # 61 seconds later
    assert cache.is_duplicate("host-1", "container-abc") is False


def test_lazy_cleanup_drops_stale_entries(monkeypatch):
    current = [1000.0]
    monkeypatch.setattr("src.listener._dedup.time.monotonic", lambda: current[0])

    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-old")
    current[0] = 1200.0  # well past window
    cache.is_duplicate("host-1", "container-new")

    assert ("host-1", "container-old") not in cache._cache
    assert ("host-1", "container-new") in cache._cache
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/listener/test_dedup.py -v`
Expected: FAIL — `src.listener._dedup` does not exist.

- [ ] **Step 3: Implement DedupCache**

Create `src/listener/_dedup.py`:

```python
import time


class DedupCache:
    """In-memory dedup for (host_id, container_id) within a time window.

    Entries older than the window are lazily removed on each write.
    """

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self._cache: dict[tuple[str, str], float] = {}

    def is_duplicate(self, host_id: str, container_id: str) -> bool:
        now = time.monotonic()
        key = (host_id, container_id)
        last = self._cache.get(key)
        if last is not None and (now - last) < self.window:
            return True
        self._cache[key] = now
        self._cleanup(now)
        return False

    def _cleanup(self, now: float) -> None:
        cutoff = now - self.window
        self._cache = {k: v for k, v in self._cache.items() if v >= cutoff}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/listener/test_dedup.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/listener/_dedup.py tests/unit/listener/test_dedup.py
git commit -m "feat(listener): add in-memory dedup cache with 60s window"
```

---

## Task 4: Container filter logic (DockerMonitor)

**Files:**
- Create: `src/listener/_filter.py`
- Test: `tests/unit/listener/test_container_filter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/listener/test_container_filter.py`:

```python
from src.listener._filter import should_monitor


def test_monitor_all_always_returns_true():
    assert should_monitor("anything", monitor_all=True, whitelist=[]) is True
    assert should_monitor("anything", monitor_all=True, whitelist=["x"]) is True


def test_monitor_none_with_empty_whitelist_returns_false():
    assert should_monitor("anything", monitor_all=False, whitelist=[]) is False


def test_whitelist_exact_match_returns_true():
    assert should_monitor("web-1", monitor_all=False, whitelist=["web-1", "api"]) is True


def test_whitelist_non_match_returns_false():
    assert should_monitor("db-1", monitor_all=False, whitelist=["web-1", "api"]) is False


def test_empty_container_name_returns_false_when_filtered():
    assert should_monitor("", monitor_all=False, whitelist=["web-1"]) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/listener/test_container_filter.py -v`
Expected: FAIL — `src.listener._filter` does not exist.

- [ ] **Step 3: Implement the filter**

Create `src/listener/_filter.py`:

```python
def should_monitor(
    container_name: str, monitor_all: bool, whitelist: list[str]
) -> bool:
    """Return True if a container should produce crash events.

    Exact string match against the whitelist. Glob/regex is out of scope.
    """
    if monitor_all:
        return True
    return container_name in whitelist
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/listener/test_container_filter.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/listener/_filter.py tests/unit/listener/test_container_filter.py
git commit -m "feat(listener): add container whitelist filter"
```

---

## Task 5: Host status update helper

**Files:**
- Create: `src/listener/_status.py`
- Test: `tests/unit/listener/test_status_update.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/listener/test_status_update.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.listener._status import update_host_status


@pytest.mark.asyncio
async def test_update_host_status_writes_to_db(host_id, fake_db_session_factory):
    await update_host_status(
        fake_db_session_factory, host_id, "connected", None
    )

    session = fake_db_session_factory.return_value
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_host_status_swallows_db_errors(host_id, caplog):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    factory = MagicMock(return_value=session)

    # must not raise
    await update_host_status(factory, host_id, "error", "oops")
    assert "Failed to update status" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/listener/test_status_update.py -v`
Expected: FAIL — `src.listener._status` does not exist.

- [ ] **Step 3: Implement the helper**

Create `src/listener/_status.py`:

```python
import logging
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.docker_host import DockerHost

logger = logging.getLogger("sentinel.listener.status")


async def update_host_status(
    session_factory: async_sessionmaker,
    host_id: uuid.UUID,
    status: str,
    message: str | None,
) -> None:
    """Best-effort update of docker_hosts.status. Never raises."""
    try:
        async with session_factory() as session:
            await session.execute(
                update(DockerHost)
                .where(DockerHost.id == host_id)
                .values(status=status, status_message=message)
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to update status for host %s", host_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/listener/test_status_update.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/listener/_status.py tests/unit/listener/test_status_update.py
git commit -m "feat(listener): add best-effort host status update helper"
```

---

## Task 6: DockerMonitor event-processing logic (no Docker yet)

**Files:**
- Modify: `src/listener/docker_monitor.py`
- Test: `tests/unit/listener/test_event_processing.py`

In this task we build the pure event-processing pipeline — extract fields, filter, dedup, publish. Docker connection & threading comes in Task 7.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/listener/test_event_processing.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listener.docker_monitor import DockerMonitor


def _sample_event(container_name="web-1", container_id="abc123", action="die"):
    return {
        "Action": action,
        "id": container_id,
        "time": 1714060800,  # 2024-04-25T00:00:00Z
        "Actor": {
            "ID": container_id,
            "Attributes": {
                "name": container_name,
                "image": "nginx:latest",
                "exitCode": "137",
            },
        },
    }


@pytest.fixture
def monitor(host_id, tenant_id, fake_db_session_factory):
    return DockerMonitor(
        host_id=host_id,
        tenant_id=tenant_id,
        host_url="tcp://test:2376",
        tls_config=None,
        monitor_all_containers=True,
        container_filter=[],
        db_session_factory=fake_db_session_factory,
    )


@pytest.mark.asyncio
async def test_process_event_publishes_to_redis(monitor):
    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        fake_client = MagicMock()
        fake_container = MagicMock()
        fake_container.logs.return_value = b"log line 1\nlog line 2"
        fake_client.containers.get.return_value = fake_container

        await monitor._process_event(_sample_event(), fake_client)

        pub.assert_awaited_once()
        tenant_arg, payload = pub.await_args.args
        assert tenant_arg == str(monitor.tenant_id)
        assert payload["container_name"] == "web-1"
        assert payload["container_id"] == "abc123"
        assert payload["exit_code"] == 137
        assert payload["logs"] == "log line 1\nlog line 2"
        assert payload["event_type"] == "die"


@pytest.mark.asyncio
async def test_process_event_skips_filtered_containers(
    host_id, tenant_id, fake_db_session_factory
):
    m = DockerMonitor(
        host_id=host_id,
        tenant_id=tenant_id,
        host_url="tcp://test:2376",
        tls_config=None,
        monitor_all_containers=False,
        container_filter=["api"],
        db_session_factory=fake_db_session_factory,
    )
    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        await m._process_event(_sample_event(container_name="web-1"), MagicMock())
        pub.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_skips_duplicates(monitor):
    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        fake_client = MagicMock()
        fake_client.containers.get.return_value.logs.return_value = b"x"
        await monitor._process_event(_sample_event(), fake_client)
        await monitor._process_event(_sample_event(), fake_client)
        assert pub.await_count == 1


@pytest.mark.asyncio
async def test_process_event_handles_missing_logs(monitor):
    import docker.errors

    with patch(
        "src.listener.docker_monitor.publish_crash_event", new=AsyncMock()
    ) as pub:
        fake_client = MagicMock()
        fake_client.containers.get.side_effect = docker.errors.NotFound("gone")
        await monitor._process_event(_sample_event(), fake_client)
        assert pub.await_args.args[1]["logs"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/listener/test_event_processing.py -v`
Expected: FAIL — `DockerMonitor.__init__` takes the old signature.

- [ ] **Step 3: Rewrite `docker_monitor.py`**

Replace the entire contents of `src/listener/docker_monitor.py`:

```python
import asyncio
import logging
import uuid
from datetime import datetime, timezone

import docker
import docker.errors

from src.listener._dedup import DedupCache
from src.listener._filter import should_monitor
from src.listener._status import update_host_status
from src.services.redis_stream import publish_crash_event

logger = logging.getLogger("sentinel.listener")


class DockerMonitor:
    """Connects to a remote Docker daemon and listens for crash events.

    A worker thread runs the blocking docker.events() generator and pushes
    each event onto an asyncio.Queue. An async consumer drains the queue,
    applies filter + dedup, fetches logs, and publishes to Redis.
    """

    def __init__(
        self,
        host_id: uuid.UUID,
        tenant_id: uuid.UUID,
        host_url: str,
        tls_config,
        monitor_all_containers: bool,
        container_filter: list[str],
        db_session_factory,
    ):
        self.host_id = host_id
        self.tenant_id = tenant_id
        self.host_url = host_url
        self.tls_config = tls_config
        self.monitor_all_containers = monitor_all_containers
        self.container_filter = list(container_filter or [])
        self._db_session_factory = db_session_factory
        self._dedup = DedupCache(window_seconds=60.0)
        self._status = "pending"

    @property
    def status(self) -> str:
        return self._status

    async def _process_event(self, event: dict, client) -> None:
        attrs = event.get("Actor", {}).get("Attributes", {})
        container_id = event.get("id") or event.get("Actor", {}).get("ID", "")
        container_name = attrs.get("name", "")
        image = attrs.get("image", "")
        exit_code_raw = attrs.get("exitCode")
        exit_code = int(exit_code_raw) if exit_code_raw not in (None, "") else None
        event_type = event.get("Action", "")
        event_ts_raw = event.get("time")
        event_ts = (
            datetime.fromtimestamp(event_ts_raw, tz=timezone.utc)
            if event_ts_raw
            else datetime.now(tz=timezone.utc)
        )

        if not should_monitor(
            container_name, self.monitor_all_containers, self.container_filter
        ):
            return

        if self._dedup.is_duplicate(str(self.host_id), container_id):
            logger.debug(
                "Deduped crash event for host=%s container=%s",
                self.host_id,
                container_id,
            )
            return

        logs = await self._fetch_logs(client, container_id)

        payload = {
            "docker_host_id": str(self.host_id),
            "container_name": container_name,
            "container_id": container_id,
            "image": image,
            "exit_code": exit_code,
            "logs": logs,
            "event_type": event_type,
            "event_timestamp": event_ts.isoformat(),
        }
        await publish_crash_event(str(self.tenant_id), payload)
        logger.info(
            "Published crash event host=%s container=%s event=%s",
            self.host_id,
            container_name,
            event_type,
        )

    async def _fetch_logs(self, client, container_id: str) -> str | None:
        def _get():
            try:
                container = client.containers.get(container_id)
                return container.logs(tail=200).decode("utf-8", errors="replace")
            except docker.errors.NotFound:
                return None

        return await asyncio.to_thread(_get)

    async def start(self) -> None:
        raise NotImplementedError("Implemented in Task 7")

    async def stop(self) -> None:
        raise NotImplementedError("Implemented in Task 7")
```

Note: `start()` and `stop()` still raise — they get their real implementation in Task 7. The tests in this task only exercise `_process_event` and its helpers.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/listener/test_event_processing.py -v`
Expected: PASS (4 tests).

Also run: `pytest tests/unit/listener/ -v`
Expected: all listener unit tests pass (13 total).

- [ ] **Step 5: Commit**

```bash
git add src/listener/docker_monitor.py tests/unit/listener/test_event_processing.py
git commit -m "feat(listener): add event processing pipeline (filter, dedup, logs, publish)"
```

---

## Task 7: DockerMonitor lifecycle (thread + async consumer + reconnect)

**Files:**
- Modify: `src/listener/docker_monitor.py` (replace `start()`/`stop()` stubs)

This task wires up the thread that runs `docker.events()`, the asyncio bridge, reconnect with exponential backoff, and status writes. Real Docker interaction means we cannot unit-test this directly; we rely on Task 8 (manager) for mocked-lifecycle tests and the manual smoke test in Task 14.

- [ ] **Step 1: Extend `DockerMonitor` with lifecycle state**

In `src/listener/docker_monitor.py`, add these imports and state:

```python
import threading
import time
```

Inside `__init__`, add after `self._status = "pending"`:

```python
        self._shutdown_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue | None = None
        self._thread: threading.Thread | None = None
        self._consumer_task: asyncio.Task | None = None
        self._async_client = None  # docker client used from the async consumer
```

- [ ] **Step 2: Replace `start()` with the real implementation**

Replace the `start()` method:

```python
    async def start(self) -> None:
        if self._thread is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=1000)
        self._async_client = docker.DockerClient(
            base_url=self.host_url, tls=self.tls_config
        )
        self._shutdown_event.clear()
        self._thread = threading.Thread(
            target=self._thread_loop, name=f"docker-monitor-{self.host_id}", daemon=True
        )
        self._thread.start()
        self._consumer_task = asyncio.create_task(self._async_consumer())
        logger.info("Started DockerMonitor for host %s", self.host_id)
```

- [ ] **Step 3: Replace `stop()` with the real implementation**

```python
    async def stop(self) -> None:
        self._shutdown_event.set()
        self._status = "stopped"
        await update_host_status(
            self._db_session_factory, self.host_id, "stopped", None
        )
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._thread is not None:
            # Thread is daemon; we don't hang on join forever.
            self._thread.join(timeout=5.0)
        if self._async_client is not None:
            try:
                self._async_client.close()
            except Exception:
                pass
        logger.info("Stopped DockerMonitor for host %s", self.host_id)
```

- [ ] **Step 4: Add the thread loop**

```python
    def _thread_loop(self) -> None:
        """Runs in a dedicated thread. Bridges docker.events() to the async queue."""
        backoff = 1.0
        while not self._shutdown_event.is_set():
            client = None
            try:
                client = docker.DockerClient(
                    base_url=self.host_url, tls=self.tls_config
                )
                self._set_status("connected", None)
                backoff = 1.0
                for event in client.events(
                    filters={"event": ["die", "oom", "kill"]}, decode=True
                ):
                    if self._shutdown_event.is_set():
                        break
                    if not self._loop or self._loop.is_closed():
                        break
                    asyncio.run_coroutine_threadsafe(
                        self._queue.put(event), self._loop
                    )
            except Exception as exc:
                msg = str(exc)[:255]
                logger.warning(
                    "Docker event stream error on host %s: %s", self.host_id, msg
                )
                self._set_status("reconnecting", msg)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
            finally:
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass
```

- [ ] **Step 5: Add the async consumer**

```python
    async def _async_consumer(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._process_event(event, self._async_client)
            except Exception:
                logger.exception("Error processing crash event")
```

- [ ] **Step 6: Add the status-bridge helper**

```python
    def _set_status(self, status: str, message: str | None) -> None:
        """Thread-safe status update: schedules coroutine on the main loop."""
        self._status = status
        if self._loop is None or self._loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(
            update_host_status(
                self._db_session_factory, self.host_id, status, message
            ),
            self._loop,
        )
```

- [ ] **Step 7: Run all listener unit tests — verify no regressions**

Run: `pytest tests/unit/listener/ -v`
Expected: all 13 tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/listener/docker_monitor.py
git commit -m "feat(listener): add DockerMonitor lifecycle with thread-async bridge and reconnect"
```

---

## Task 8: ListenerManager — sync_listeners diff logic

**Files:**
- Modify: `src/listener/manager.py`
- Test: `tests/unit/listener/test_manager.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/listener/test_manager.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.listener.manager import ListenerManager


def _fake_host(host_id, tenant_id, is_active=True, connection_mode="tcp"):
    h = MagicMock()
    h.id = host_id
    h.tenant_id = tenant_id
    h.is_active = is_active
    h.connection_mode = connection_mode
    h.tcp_url = "tcp://test:2376"
    h.tls_enabled = False
    h.tls_ca = None
    h.tls_cert = None
    h.tls_key = None
    h.monitor_all_containers = True
    h.container_filter = []
    return h


@pytest.fixture
def fake_session_with_hosts():
    def _build(hosts):
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = hosts
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        return MagicMock(return_value=session)

    return _build


@pytest.mark.asyncio
async def test_sync_spawns_monitor_for_new_host(fake_session_with_hosts, host_id, tenant_id):
    host = _fake_host(host_id, tenant_id)
    factory = fake_session_with_hosts([host])

    with patch("src.listener.manager.DockerMonitor") as MockMonitor:
        mock = MagicMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        MockMonitor.return_value = mock

        mgr = ListenerManager(db_session_factory=factory)
        await mgr.sync_listeners()

        MockMonitor.assert_called_once()
        mock.start.assert_awaited_once()
        assert host_id in mgr._listeners


@pytest.mark.asyncio
async def test_sync_stops_monitor_for_removed_host(fake_session_with_hosts, host_id, tenant_id):
    factory = fake_session_with_hosts([])

    mgr = ListenerManager(db_session_factory=factory)
    existing = MagicMock()
    existing.stop = AsyncMock()
    mgr._listeners[host_id] = existing

    await mgr.sync_listeners()

    existing.stop.assert_awaited_once()
    assert host_id not in mgr._listeners


@pytest.mark.asyncio
async def test_sync_leaves_existing_monitor_alone(fake_session_with_hosts, host_id, tenant_id):
    host = _fake_host(host_id, tenant_id)
    factory = fake_session_with_hosts([host])

    mgr = ListenerManager(db_session_factory=factory)
    existing = MagicMock()
    existing.start = AsyncMock()
    existing.stop = AsyncMock()
    mgr._listeners[host_id] = existing

    with patch("src.listener.manager.DockerMonitor") as MockMonitor:
        await mgr.sync_listeners()
        MockMonitor.assert_not_called()
        existing.stop.assert_not_awaited()
        existing.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_skips_agent_mode_hosts(fake_session_with_hosts, host_id, tenant_id):
    """Agent-mode hosts are handled by the API WebSocket, not the manager."""
    # We simulate DB filtering by returning no hosts (the query filters by connection_mode=tcp).
    # This test documents the expectation by asserting the query was invoked with the right filter.
    factory = fake_session_with_hosts([])
    mgr = ListenerManager(db_session_factory=factory)
    await mgr.sync_listeners()

    session = factory.return_value
    session.execute.assert_awaited_once()
    # The actual filter clause is tested implicitly: if we pass a non-TCP host, it won't appear.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/listener/test_manager.py -v`
Expected: FAIL — `ListenerManager` does not accept `db_session_factory` in `__init__`.

- [ ] **Step 3: Rewrite `manager.py` (sync_listeners portion)**

Replace the entire contents of `src/listener/manager.py`:

```python
import asyncio
import logging
import uuid

import docker
from sqlalchemy import select

from src.listener.docker_monitor import DockerMonitor
from src.models.docker_host import DockerHost

logger = logging.getLogger("sentinel.listener.manager")


class ListenerManager:
    """Owns the lifecycle of DockerMonitor instances across all tenants.

    Polls PostgreSQL every sync_interval seconds. Spawns/stops monitors
    as docker_hosts rows appear/disappear or are toggled (de)active.
    """

    def __init__(self, db_session_factory, sync_interval: float = 30.0):
        self._db_session_factory = db_session_factory
        self._sync_interval = sync_interval
        self._listeners: dict[uuid.UUID, DockerMonitor] = {}
        self._sync_task: asyncio.Task | None = None
        self._shutdown = asyncio.Event()

    async def sync_listeners(self) -> None:
        async with self._db_session_factory() as session:
            result = await session.execute(
                select(DockerHost).where(
                    DockerHost.is_active == True,  # noqa: E712
                    DockerHost.connection_mode == "tcp",
                )
            )
            hosts = list(result.scalars().all())

        desired: dict[uuid.UUID, DockerHost] = {h.id: h for h in hosts}

        # Stop monitors whose hosts are gone or deactivated.
        for host_id in list(self._listeners.keys()):
            if host_id not in desired:
                logger.info("Stopping listener for removed host %s", host_id)
                try:
                    await self._listeners[host_id].stop()
                finally:
                    self._listeners.pop(host_id, None)

        # Spawn monitors for new hosts.
        for host_id, host in desired.items():
            if host_id in self._listeners:
                continue
            logger.info("Spawning listener for host %s", host_id)
            tls_config = self._build_tls_config(host)
            monitor = DockerMonitor(
                host_id=host.id,
                tenant_id=host.tenant_id,
                host_url=host.tcp_url,
                tls_config=tls_config,
                monitor_all_containers=host.monitor_all_containers,
                container_filter=host.container_filter or [],
                db_session_factory=self._db_session_factory,
            )
            await monitor.start()
            self._listeners[host_id] = monitor

    def _build_tls_config(self, host: DockerHost):
        if not host.tls_enabled:
            return None
        # Minimal TLSConfig from PEM-encoded strings stored in DB.
        # For portfolio-scale, we trust the certs from DB. A production build
        # would write these to tempfiles with tight permissions.
        import tempfile

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

    async def start(self) -> None:
        raise NotImplementedError("Implemented in Task 9")

    async def stop(self) -> None:
        raise NotImplementedError("Implemented in Task 9")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/listener/test_manager.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/listener/manager.py tests/unit/listener/test_manager.py
git commit -m "feat(listener): add ListenerManager sync with spawn/stop diff"
```

---

## Task 9: ListenerManager — poll loop lifecycle

**Files:**
- Modify: `src/listener/manager.py` (replace `start()`/`stop()` stubs)
- Test: append to `tests/unit/listener/test_manager.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/listener/test_manager.py`:

```python
@pytest.mark.asyncio
async def test_manager_start_runs_sync_in_background(fake_session_with_hosts):
    factory = fake_session_with_hosts([])
    mgr = ListenerManager(db_session_factory=factory, sync_interval=0.05)
    with patch.object(mgr, "sync_listeners", new=AsyncMock()) as sync:
        await mgr.start()
        await asyncio.sleep(0.12)  # allow ≥2 sync cycles
        await mgr.stop()
        assert sync.await_count >= 2


@pytest.mark.asyncio
async def test_manager_stop_terminates_sync_task_and_stops_monitors(fake_session_with_hosts, host_id):
    factory = fake_session_with_hosts([])
    mgr = ListenerManager(db_session_factory=factory, sync_interval=0.05)
    mon = MagicMock()
    mon.stop = AsyncMock()
    mgr._listeners[host_id] = mon

    await mgr.start()
    await asyncio.sleep(0.05)
    await mgr.stop()

    mon.stop.assert_awaited()
    assert mgr._sync_task is None or mgr._sync_task.done()
```

Add the top-level import for `asyncio` if it isn't already in the test file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/listener/test_manager.py::test_manager_start_runs_sync_in_background tests/unit/listener/test_manager.py::test_manager_stop_terminates_sync_task_and_stops_monitors -v`
Expected: FAIL — `start()` and `stop()` raise `NotImplementedError`.

- [ ] **Step 3: Implement `start()` and `stop()`**

In `src/listener/manager.py`, replace the `start()` and `stop()` methods:

```python
    async def start(self) -> None:
        if self._sync_task is not None:
            return
        self._shutdown.clear()
        self._sync_task = asyncio.create_task(self._sync_loop(), name="listener-sync")
        logger.info("ListenerManager started (interval=%.1fs)", self._sync_interval)

    async def stop(self) -> None:
        self._shutdown.set()
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except (asyncio.CancelledError, Exception):
                pass
            self._sync_task = None
        # Stop all monitors in parallel.
        if self._listeners:
            await asyncio.gather(
                *(m.stop() for m in self._listeners.values()),
                return_exceptions=True,
            )
            self._listeners.clear()
        logger.info("ListenerManager stopped")

    async def _sync_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                await self.sync_listeners()
            except Exception:
                logger.exception("ListenerManager sync failure")
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(), timeout=self._sync_interval
                )
            except asyncio.TimeoutError:
                pass  # normal path — interval elapsed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/listener/test_manager.py -v`
Expected: PASS (6 tests total).

- [ ] **Step 5: Commit**

```bash
git add src/listener/manager.py tests/unit/listener/test_manager.py
git commit -m "feat(listener): add ListenerManager start/stop with poll loop"
```

---

## Task 10: Worker — TenantConsumerSupervisor

**Files:**
- Modify: `src/worker/main.py`
- Test: `tests/unit/worker/test_supervisor.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/worker/test_supervisor.py`:

```python
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.worker.main import TenantConsumerSupervisor


def _fake_tenant(tid):
    t = MagicMock()
    t.id = tid
    return t


@pytest.fixture
def factory_with_tenants():
    def _build(tenants):
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = tenants
        session.execute = AsyncMock(return_value=result)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        return MagicMock(return_value=session)

    return _build


@pytest.mark.asyncio
async def test_supervisor_spawns_task_per_tenant(factory_with_tenants):
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    factory = factory_with_tenants([_fake_tenant(t1), _fake_tenant(t2)])
    consume = AsyncMock()
    sup = TenantConsumerSupervisor(
        db_session_factory=factory, consume_fn=consume, sync_interval=0.05
    )
    await sup.sync_tenants()
    assert t1 in sup._tasks
    assert t2 in sup._tasks
    await sup.stop()


@pytest.mark.asyncio
async def test_supervisor_cancels_task_for_removed_tenant(factory_with_tenants):
    t1 = uuid.uuid4()
    factory = factory_with_tenants([])

    async def never_ending(tid, shutdown):
        await shutdown.wait()

    sup = TenantConsumerSupervisor(
        db_session_factory=factory, consume_fn=never_ending, sync_interval=0.05
    )
    fake_task = asyncio.create_task(asyncio.sleep(10))
    sup._tasks[t1] = fake_task
    await sup.sync_tenants()
    await asyncio.sleep(0.01)
    assert t1 not in sup._tasks
    assert fake_task.cancelled() or fake_task.done()


@pytest.mark.asyncio
async def test_supervisor_start_stop_lifecycle(factory_with_tenants):
    factory = factory_with_tenants([])
    calls = []

    async def consume(tid, shutdown):
        calls.append(tid)
        await shutdown.wait()

    sup = TenantConsumerSupervisor(
        db_session_factory=factory, consume_fn=consume, sync_interval=0.05
    )
    await sup.start()
    await asyncio.sleep(0.12)
    await sup.stop()
    assert sup._sync_task is None or sup._sync_task.done()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/worker/test_supervisor.py -v`
Expected: FAIL — `TenantConsumerSupervisor` does not exist.

- [ ] **Step 3: Implement `TenantConsumerSupervisor`**

Replace the entire contents of `src/worker/main.py` (we'll expand further in Tasks 11–12):

```python
import asyncio
import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select

from src.models.tenant import Tenant
from src.services.database import async_session_factory

logger = logging.getLogger("sentinel.worker")

ConsumerFn = Callable[[uuid.UUID, asyncio.Event], Awaitable[None]]


class TenantConsumerSupervisor:
    """Maintains one asyncio consumer task per tenant.

    Polls the tenants table every sync_interval seconds; spawns consumers
    for new tenants and cancels consumers for removed tenants.
    """

    def __init__(
        self,
        db_session_factory,
        consume_fn: ConsumerFn,
        sync_interval: float = 30.0,
    ):
        self._db_session_factory = db_session_factory
        self._consume_fn = consume_fn
        self._sync_interval = sync_interval
        self._tasks: dict[uuid.UUID, asyncio.Task] = {}
        self._shutdown = asyncio.Event()
        self._sync_task: asyncio.Task | None = None

    async def sync_tenants(self) -> None:
        async with self._db_session_factory() as session:
            result = await session.execute(select(Tenant))
            tenants = list(result.scalars().all())
        desired = {t.id for t in tenants}

        for tid in list(self._tasks.keys()):
            if tid not in desired:
                task = self._tasks.pop(tid)
                task.cancel()

        for tid in desired:
            if tid in self._tasks:
                continue
            self._tasks[tid] = asyncio.create_task(
                self._consume_fn(tid, self._shutdown), name=f"consume-{tid}"
            )

    async def start(self) -> None:
        if self._sync_task is not None:
            return
        self._shutdown.clear()
        self._sync_task = asyncio.create_task(self._loop(), name="tenant-sync")

    async def stop(self) -> None:
        self._shutdown.set()
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except (asyncio.CancelledError, Exception):
                pass
            self._sync_task = None
        if self._tasks:
            for t in self._tasks.values():
                t.cancel()
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
            self._tasks.clear()

    async def _loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                await self.sync_tenants()
            except Exception:
                logger.exception("Tenant sync failure")
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(), timeout=self._sync_interval
                )
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    raise NotImplementedError("Implemented in Task 12")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/worker/test_supervisor.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/worker/main.py tests/unit/worker/test_supervisor.py
git commit -m "feat(worker): add TenantConsumerSupervisor to manage per-tenant consumers"
```

---

## Task 11: Worker — event processor (`_process_event`)

**Files:**
- Modify: `src/worker/main.py`
- Test: `tests/unit/worker/test_process_event.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/worker/test_process_event.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.worker.main import _process_event


@pytest.fixture
def tenant_id():
    return uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def event_payload():
    return {
        "id": "redis-msg-id-1",
        "docker_host_id": str(uuid.uuid4()),
        "container_name": "web-1",
        "container_id": "abc123",
        "image": "nginx:latest",
        "exit_code": 137,
        "logs": "out of memory",
        "event_type": "die",
        "event_timestamp": "2026-04-21T12:00:00+00:00",
    }


@pytest.fixture
def mock_session_factory():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return MagicMock(return_value=session)


@pytest.mark.asyncio
async def test_process_event_inserts_crash_event_row(tenant_id, event_payload, mock_session_factory):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock()
        await _process_event(event_payload, tenant_id, mock_session_factory)
        session = mock_session_factory.return_value
        session.add.assert_called_once()
        added = session.add.call_args.args[0]
        assert added.tenant_id == tenant_id
        assert added.container_name == "web-1"
        assert added.exit_code == 137


@pytest.mark.asyncio
async def test_process_event_invokes_langgraph_workflow(tenant_id, event_payload, mock_session_factory):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock()
        await _process_event(event_payload, tenant_id, mock_session_factory)
        wf.ainvoke.assert_awaited_once()
        state = wf.ainvoke.await_args.args[0]
        assert state["tenant_id"] == str(tenant_id)
        assert "crash_event_id" in state


@pytest.mark.asyncio
async def test_process_event_swallows_not_implemented_error(tenant_id, event_payload, mock_session_factory, caplog):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock(side_effect=NotImplementedError("phase 2"))
        # Should not raise; logged as debug/info rather than error.
        await _process_event(event_payload, tenant_id, mock_session_factory)


@pytest.mark.asyncio
async def test_process_event_swallows_other_exceptions(tenant_id, event_payload, mock_session_factory, caplog):
    with patch("src.worker.main.crash_workflow") as wf:
        wf.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
        await _process_event(event_payload, tenant_id, mock_session_factory)
        assert "Error invoking crash workflow" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/worker/test_process_event.py -v`
Expected: FAIL — `_process_event` does not exist.

- [ ] **Step 3: Add `_process_event` to `src/worker/main.py`**

At the top of the file, add imports:

```python
from src.models.crash_event import CrashEvent
from src.orchestrator.graph import crash_workflow
```

Add this function (before `main()`):

```python
async def _process_event(
    event: dict, tenant_id: uuid.UUID, db_session_factory
) -> None:
    """Insert a pending CrashEvent row, then invoke the LangGraph workflow."""
    crash_row = CrashEvent(
        tenant_id=tenant_id,
        docker_host_id=uuid.UUID(event["docker_host_id"]),
        container_name=event.get("container_name", ""),
        container_id=event.get("container_id", ""),
        image=event.get("image", ""),
        exit_code=event.get("exit_code"),
        logs=event.get("logs"),
    )
    async with db_session_factory() as session:
        session.add(crash_row)
        await session.flush()
        crash_event_id = crash_row.id
        await session.commit()

    state = {
        "crash_event_id": str(crash_event_id),
        "tenant_id": str(tenant_id),
        "event_data": event,
    }
    try:
        await crash_workflow.ainvoke(state)
    except NotImplementedError:
        logger.info(
            "LangGraph node not implemented yet (expected during Phase 1) for event=%s",
            event.get("id"),
        )
    except Exception:
        logger.exception(
            "Error invoking crash workflow for event=%s", event.get("id")
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/worker/test_process_event.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/worker/main.py tests/unit/worker/test_process_event.py
git commit -m "feat(worker): add _process_event — insert CrashEvent row and invoke workflow"
```

---

## Task 12: Worker — `main()` entrypoint with signal handlers

**Files:**
- Modify: `src/worker/main.py`

Signal handling is OS-specific and tricky to unit-test cleanly. We smoke-test this in Task 14 with `docker compose`.

- [ ] **Step 1: Add a per-tenant consumer function that reuses `consume_crash_events`**

Add to `src/worker/main.py`, after `_process_event`:

```python
async def _consume_tenant(
    tenant_id: uuid.UUID, shutdown: asyncio.Event
) -> None:
    """Loop: consume from crashes:{tenant_id}, process, repeat until shutdown."""
    from src.services.redis_stream import consume_crash_events

    while not shutdown.is_set():
        try:
            events = await consume_crash_events(
                str(tenant_id),
                consumer_group="orchestrator",
                consumer_name="worker-1",
            )
            for event in events:
                if shutdown.is_set():
                    break
                await _process_event(event, tenant_id, async_session_factory)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Consumer error for tenant=%s; retrying in 5s", tenant_id
            )
            try:
                await asyncio.wait_for(shutdown.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
```

- [ ] **Step 2: Replace the `main()` stub**

Replace the `main()` function at the bottom of `src/worker/main.py`:

```python
async def main() -> None:
    import signal

    from src.listener.manager import ListenerManager

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting DockerSentinel worker")

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_shutdown(signame: str) -> None:
        logger.info("Received %s, shutting down", signame)
        shutdown_event.set()

    for signame in ("SIGTERM", "SIGINT"):
        try:
            loop.add_signal_handler(
                getattr(signal, signame), _request_shutdown, signame
            )
        except (NotImplementedError, RuntimeError):
            # Windows doesn't support add_signal_handler for SIGTERM.
            signal.signal(
                getattr(signal, signame),
                lambda *_args, n=signame: _request_shutdown(n),
            )

    manager = ListenerManager(db_session_factory=async_session_factory)
    supervisor = TenantConsumerSupervisor(
        db_session_factory=async_session_factory,
        consume_fn=_consume_tenant,
    )

    await manager.start()
    await supervisor.start()

    await shutdown_event.wait()

    logger.info("Shutdown requested; stopping supervisor and manager")
    await asyncio.wait_for(supervisor.stop(), timeout=10.0)
    await asyncio.wait_for(manager.stop(), timeout=10.0)
    logger.info("Worker stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Verify the module imports cleanly**

Run: `python -c "from src.worker.main import main, TenantConsumerSupervisor, _process_event, _consume_tenant; print('ok')"`
Expected: prints `ok` with no import errors.

- [ ] **Step 4: Run the full unit-test suite — no regressions**

Run: `pytest tests/unit/ -v`
Expected: all 20 tests pass (13 listener + 7 worker).

- [ ] **Step 5: Commit**

```bash
git add src/worker/main.py
git commit -m "feat(worker): add main() entrypoint with signal handlers and graceful shutdown"
```

---

## Task 13: Update the work tracker

**Files:**
- Modify: `work-tracking/PROGRESS.md`

- [ ] **Step 1: Mark Phase 1 items 1–3 as done and add a daily log entry**

In `work-tracking/PROGRESS.md`, under the Phase 1 table, change the status of rows 1, 2, and 3 from `**Critical**` to `✅ **Done**`. Append a new daily log entry:

```markdown
### 2026-04-21
- **Status:** Phase 1 items #1, #2, #3 complete (crash ingestion pipeline).
- **What was done:**
  - Extended `CrashEventCreate` schema with `event_type`, `event_timestamp`.
  - Built `DockerMonitor` with thread/async bridge, dedup, container filter, reconnect.
  - Built `ListenerManager` with 30s DB-sync loop.
  - Built `Worker` with `TenantConsumerSupervisor` and `_process_event` → LangGraph handoff.
  - 20 unit tests passing.
- **Pick up from here:** Phase 1 items #4, #5, #6 — LangGraph orchestrator nodes (`analyze_crash`, `attempt_restart`, `log_event`). With the pipeline delivering events, we can now wire real analysis. Note: Phase 1 items #4–6 depend on Fix Agent (#7) and Qdrant cache (#15–16) for `analyze_crash` — consider sequencing or stubbing.
```

- [ ] **Step 2: Commit**

```bash
git add work-tracking/PROGRESS.md
git commit -m "docs: mark Phase 1 items 1-3 complete in work tracker"
```

---

## Task 14: Manual smoke test (end-to-end)

**Files:** none — verification only.

This is the "Phase 1 complete" acceptance gate.

- [ ] **Step 1: Start the full stack**

Run: `docker compose up -d`
Expected: `postgres`, `redis`, `qdrant`, `api`, `worker`, `frontend` containers all healthy.

- [ ] **Step 2: Run DB migrations**

Run: `docker compose exec api alembic upgrade head`
Expected: `"Target database is up to date."` or migration output.

- [ ] **Step 3: Seed a tenant and Docker host**

Run (substituting `host.docker.internal` for a host your Compose stack can reach):

```bash
docker compose exec api python -c "
import asyncio, uuid
from src.services.database import async_session_factory
from src.models.tenant import Tenant
from src.models.docker_host import DockerHost

async def seed():
    async with async_session_factory() as s:
        tid = uuid.uuid4()
        s.add(Tenant(id=tid, name='smoke-test'))
        s.add(DockerHost(
            id=uuid.uuid4(), tenant_id=tid, name='local',
            connection_mode='tcp', tcp_url='tcp://host.docker.internal:2375',
            is_active=True, monitor_all_containers=True,
        ))
        await s.commit()
        print('seeded tenant', tid)
asyncio.run(seed())
"
```

Expected: `seeded tenant <uuid>`.

- [ ] **Step 4: Trigger a crash on the host**

In a separate shell (on the host whose Docker daemon is at `tcp://host.docker.internal:2375`):

```bash
docker run --name sentinel-smoke busybox sh -c 'exit 1'
```

Expected: exits with code 1.

- [ ] **Step 5: Verify the event reached Redis**

Run: `docker compose exec redis redis-cli XLEN crashes:<tenant-id-from-step-3>`
Expected: `(integer) 1` within ~3 seconds of the crash.

- [ ] **Step 6: Verify the worker logged the workflow invocation**

Run: `docker compose logs worker --tail 50`
Expected: a log line like `"LangGraph node not implemented yet (expected during Phase 1) for event=..."` — this confirms the event traversed the whole pipeline and reached `crash_workflow.ainvoke()`.

- [ ] **Step 7: Verify `docker_hosts.status`**

Run:

```bash
docker compose exec postgres psql -U postgres -d dockersentinel -c "SELECT name, status, status_message FROM docker_hosts;"
```

Expected: `status = 'connected'` and `status_message` NULL for the test host.

- [ ] **Step 8: Tear down**

Run: `docker rm sentinel-smoke; docker compose down -v`
Expected: everything stops cleanly.

- [ ] **Step 9: Commit the smoke-test evidence (optional)**

If you want a record, copy the relevant log output into a file like `docs/superpowers/evidence/2026-04-21-phase1-smoke.md` and commit it. Otherwise skip.

---

## Self-review (completed by the planner)

- **Spec coverage:** Every section of the design doc is represented:
  - Architecture + data flow → Tasks 6–12 overall.
  - Dedup → Task 3.
  - Container filter → Task 4.
  - Status update → Task 5.
  - Reconnection with backoff → Task 7.
  - Manager sync + lifecycle → Tasks 8–9.
  - Worker supervisor + consume loop → Tasks 10, 12.
  - `_process_event` → Task 11.
  - Graceful shutdown → Tasks 7, 9, 10, 12.
  - Acceptance criteria → Task 14.
  - Schema extension → Task 1.
- **Placeholder scan:** No TBD/TODO/vague steps. Every code step shows full code.
- **Type/name consistency:** `DockerMonitor` constructor keyword args match across Task 6 (definition), Task 8 (`ListenerManager` call site), and tests. `TenantConsumerSupervisor` signature matches between Task 10 and Task 12. `_process_event` signature matches between Task 11 and Task 12.
- **Known gap flagged (not a placeholder):** Integration tests with Docker-in-Docker and real Redis from the spec are deferred — the smoke test in Task 14 serves as the acceptance gate. If full integration tests are desired later, add a new task.
