# Crash Ingestion Pipeline — Design

**Date:** 2026-04-21
**Scope:** Phase 1, Items #1–3 from `work-tracking/PROGRESS.md` — the three components that turn Docker daemon events into LangGraph workflow invocations.

- `src/listener/docker_monitor.py` — listens on one Docker host
- `src/listener/manager.py` — owns the set of active monitors
- `src/worker/main.py` — consumes Redis streams, invokes LangGraph

## Goals

1. A crash on any registered Docker host results in a `CrashEvent` payload arriving at the LangGraph orchestrator.
2. Transient host failures self-heal without operator intervention.
3. Crash-looping containers don't flood the pipeline with duplicate events.
4. Tenant isolation: one noisy tenant cannot starve another.
5. At-least-once delivery for crash events (missed events = missed alerts).

## Non-goals

- Scaling to 1000s of Docker hosts per worker process (thread-per-host is fine for portfolio scale).
- Agent-mode hosts (`connection_mode = "agent"`). Those push events via WebSocket directly to the API server, bypassing this pipeline. Handled separately.
- Semantic deduplication of similar crashes. That is Qdrant's job (Phase 3).
- Horizontal scaling across worker replicas. Single worker process; multi-replica is future work.

## Architecture

Three components, one process:

```
┌──────────────────────────────────────────────────────────────────┐
│                     API / DB (PostgreSQL)                         │
│  docker_hosts table: tenant_id, tcp_url, tls_*, status, is_active │
└──────────────────────────────────────────────────────────────────┘
         ▲                                           ▲
         │ (1) polls every 30s                       │ (5) updates status
         │                                           │
┌────────┴──────────┐                       ┌────────┴───────────┐
│  ListenerManager  │──(2) spawns──────────▶│   DockerMonitor    │
│  (asyncio task)   │                       │  (1 per host)      │
└───────────────────┘                       └────────┬───────────┘
                                                     │ (3) thread runs
                                                     │     docker.events()
                                                     │ ┌───────────────┐
                                                     └▶│ worker thread │
                                                       │ blocking loop │
                                                       └───────┬───────┘
                                                               │ (4) asyncio.Queue
                                                               ▼
                                           ┌─────────────────────────────────┐
                                           │ capture logs + dedup check      │
                                           │ → publish to Redis stream       │
                                           │   crashes:{tenant_id}           │
                                           └─────────────────┬───────────────┘
                                                             │
                                                             ▼
                                            ┌──────────────────────────────┐
                                            │    Redis Streams              │
                                            │  crashes:{tenant_id}          │
                                            └──────────────┬───────────────┘
                                                           │ XREADGROUP
                                                           ▼
                                            ┌──────────────────────────────┐
                                            │  Worker (src/worker/main.py)  │
                                            │  - polls tenant list from DB  │
                                            │  - 1 consumer task per tenant │
                                            │  - invokes LangGraph workflow │
                                            └──────────────────────────────┘
```

### End-to-end flow

1. A container on a registered host exits with code 137 (OOM kill).
2. The `DockerMonitor` worker thread for that host receives the `die` event from `docker.client.events()`.
3. Thread pushes raw event dict into a per-monitor `asyncio.Queue`.
4. The monitor's async consumer drains the queue, and for each event:
   - Applies container filter (`monitor_all_containers`, `container_filter`).
   - Calls `container.logs(tail=200)` to capture logs while the container still exists.
   - Checks in-memory dedup map for `(host_id, container_id)`; drops if duplicate within 60s.
   - Builds a `CrashEventCreate` payload and calls `publish_crash_event(tenant_id, payload)`.
5. On any connection failure: `status` is updated in `docker_hosts`, an exponential backoff is applied, and the thread reconnects.
6. The `Worker` maintains a per-tenant consumer task. Each task does `XREADGROUP` on `crashes:{tenant_id}` with the consumer group `"orchestrator"`, deserializes, and calls `crash_workflow.ainvoke(state)`.

## Key design decisions

### Docker SDK async strategy: thread-pool

The Python `docker` SDK is synchronous. `client.events()` returns a blocking generator. We wrap it in a thread per monitor and bridge events to asyncio via an `asyncio.Queue`.

**Why:** The skeleton already commits to the `docker` SDK. Thread-per-host is a well-understood idiom and scales adequately for portfolio-level deployments. Third-party async alternatives (`aiodocker`) are less mature and handle TLS worse.

### Dedup: in-memory time-window

A `dict[tuple[host_id, container_id], float]` tracks the timestamp of the last published event. Events within 60 seconds of the last one for the same container are dropped.

**Why:** Crash loops commonly fire events every few seconds. Naive publishing would create notification spam and wasted LLM calls. 60s is short enough to catch genuine re-crashes, long enough to suppress loops. In-memory is sufficient for single-process deployment.

### Log capture: at event time, in the listener

When a `die`/`oom`/`kill` event arrives, the listener immediately calls `container.logs(tail=200)` on the same Docker client.

**Why:** `docker run --rm` containers are auto-removed after exit. Delaying log fetch to the worker risks the container disappearing before logs are captured. The cost of the extra API call inside the listener thread is negligible (milliseconds).

### Reconnection: retry forever with live status

On any error, the monitor updates `docker_hosts.status` to `"error"` or `"reconnecting"`, records a `status_message`, applies exponential backoff (capped at 60s), and tries again. Monitors never give up on their own.

**Why:** Infra tools should self-heal. Failure signalling belongs in the DB `status` column (already present in the model), so the UI can show "unreachable" without the system silently deciding to stop monitoring. Only operator action (toggling `is_active = false`) stops a monitor.

### Multi-tenant consumption: consumer group per tenant stream

The worker queries `tenants` every 30s, maintains a `{tenant_id: asyncio.Task}` dict, and each task runs a `XREADGROUP` consumer on `crashes:{tenant_id}` with group `"orchestrator"` and consumer name `"worker-1"`.

**Why:** Consumer groups provide at-least-once delivery with acks — critical for a crash-detection system. Per-tenant tasks prevent a noisy tenant from starving others. Matches the existing `src/services/redis_stream.py` pattern.

## Component specifications

### `DockerMonitor` (`src/listener/docker_monitor.py`)

One instance per active `docker_hosts` row with `connection_mode = "tcp"` and `is_active = true`.

**Constructor:**

```python
DockerMonitor(
    host_id: uuid.UUID,
    tenant_id: uuid.UUID,
    host_url: str,
    tls_config: docker.tls.TLSConfig | None,
    monitor_all_containers: bool,
    container_filter: list[str],
    db_session_factory: async_sessionmaker,
)
```

**Public methods:**
- `async start()` — spawns the worker thread and async consumer task, returns immediately.
- `async stop()` — signals shutdown, joins thread (5s timeout), closes Docker client.
- `@property status` — current status: `"connected"`, `"reconnecting"`, `"error"`, `"stopped"`.

**Internal:**
- `_thread_loop()` — runs in `threading.Thread`:
  1. `docker.DockerClient(base_url=host_url, tls=tls_config)`
  2. Update `status = "connected"` (schedule coroutine on main loop via `asyncio.run_coroutine_threadsafe`).
  3. Iterate `client.events(filters={'event': ['die', 'oom', 'kill']}, decode=True)`.
  4. For each event: `asyncio.run_coroutine_threadsafe(self._queue.put(event), loop)`.
  5. On exception: update `status = "reconnecting"` with message, `time.sleep(backoff)`, loop back to step 1.
  6. Shutdown flag exits the loop cleanly.
- `_async_consumer()` — `async for event in queue.get()`:
  1. Extract `container_id`, `container_name`, `image`, `exit_code`.
  2. Filter: if not `monitor_all_containers` and `container_name` not in `container_filter` (exact string match against the list stored in the JSONB column; glob/regex is out of scope), skip.
  3. Dedup: if `(host_id, container_id)` in `_dedup_cache` with ts > now - 60s, skip. Else record ts.
  4. Fetch logs: `container = client.containers.get(container_id); logs = container.logs(tail=200).decode()`. On `docker.errors.NotFound`, `logs = None`.
  5. Build `CrashEventCreate` payload + `event_type`, `event_timestamp`.
  6. `await publish_crash_event(str(tenant_id), payload_dict)`.
- `_dedup_cache: dict[tuple[uuid.UUID, str], float]` — lazy cleanup: on write, drop entries older than 60s.

### `ListenerManager` (`src/listener/manager.py`)

Singleton per worker process. Instantiated by `src/worker/main.py`.

**Public methods:**
- `async start()` — kicks off the sync loop (immediate first run, then every 30s).
- `async stop()` — graceful shutdown of all monitors.
- `async sync_listeners()` — single sync pass. Exposed for tests.

**State:**
- `_listeners: dict[uuid.UUID, DockerMonitor]` — host_id → monitor.
- `_sync_task: asyncio.Task | None`
- `_shutdown: asyncio.Event`

**Sync pass:**
1. `async with db_session_factory() as s: hosts = (await s.execute(select(DockerHost).where(DockerHost.is_active == True, DockerHost.connection_mode == "tcp"))).scalars().all()`
2. Existing monitors not in `hosts`: `await monitor.stop()`, remove from dict.
3. Hosts not in `_listeners`: construct `DockerMonitor`, `await monitor.start()`, add to dict.
4. Existing monitors in `hosts`: leave alone (hot config updates are out of scope).

### `Worker` (`src/worker/main.py`)

Entrypoint via `python -m src.worker.main`.

**`async def main()`:**
1. Initialize DB session factory, Redis client.
2. Install signal handlers (SIGTERM, SIGINT → shutdown event).
3. Start `ListenerManager`.
4. Start `TenantConsumerSupervisor`.
5. `await shutdown_event.wait()`.
6. Graceful shutdown: stop supervisor, stop manager, wait for in-flight workflows (10s timeout), close resources.

**`TenantConsumerSupervisor`** (new class, can live at the bottom of `main.py` for now):
- Polls `tenants` table every 30s.
- Maintains `{tenant_id: asyncio.Task}`.
- Tenant appears → spawn `_consume_tenant(tenant_id)` task.
- Tenant disappears → cancel task.

**`_consume_tenant(tenant_id)`** — reuses `consume_crash_events` from `src/services/redis_stream.py`:
```python
while not shutdown:
    try:
        events = await consume_crash_events(tenant_id, consumer_group="orchestrator", consumer_name="worker-1")
        for event in events:
            await _process_event(event, tenant_id)
    except redis.exceptions.RedisError as e:
        logger.error(...); await asyncio.sleep(5)
```

Note: the existing helper acks on read (`XACK` inside `consume_crash_events`). For this design we accept at-least-once with a small at-most-once window for processing failures — acceptable given the orchestrator nodes raise `NotImplementedError` in Phase 1 and retrying a poison event helps no one. Move ack out of the helper when Phase 2 introduces real processing.

**`_process_event(event, tenant_id)`:**
1. Insert `CrashEvent` DB row (pending, no analysis).
2. Build state dict: `{"crash_event_id": str(row.id), "tenant_id": str(tenant_id), "event_data": event}`.
3. `await crash_workflow.ainvoke(state)` — will raise `NotImplementedError` until Phase 2, which we catch and log.
4. Ack on success OR on `NotImplementedError` (Phase 1 considered delivered once the workflow is invoked).

## Schemas

Extend `src/schemas/crash_event.py::CrashEventCreate`:

```python
class CrashEventCreate(BaseModel):
    docker_host_id: uuid.UUID
    container_name: str
    container_id: str
    image: str
    exit_code: int | None = None
    logs: str | None = None
    event_type: str | None = None          # NEW: die | oom | kill
    event_timestamp: datetime | None = None  # NEW
```

Both new fields are optional — agent-mode producers (future) and existing callers still work.

## Error handling

| Failure | Detection | Response |
|---|---|---|
| Docker host unreachable on startup | `DockerException` on client init | `status="error"`, message, backoff, retry forever |
| TLS cert invalid / auth failure | `TLSParameterError` | `status="error"` with TLS message, retry (operator fixes) |
| Event stream drops mid-session | `ConnectionError` in thread | `status="reconnecting"`, exp backoff 1→60s, reconnect |
| Log fetch fails (container auto-removed) | `docker.errors.NotFound` | Publish event with `logs=None` |
| Redis publish fails | `RedisError` | Retry 3 times with 0.5s backoff; then drop + log loudly |
| DB status update fails | `SQLAlchemyError` | Log, continue (best-effort, don't kill monitor) |
| LangGraph workflow throws | any exception | Log, ack, increment Prometheus counter (poison event) |
| Worker Redis `XREADGROUP` fails | `RedisError` | Log, backoff 5s, retry — supervisor keeps task alive |
| Tenant deleted mid-session | seen on next DB poll | Supervisor cancels that tenant's consumer task |

## Shutdown

- SIGTERM → `shutdown_event.set()`.
- `TenantConsumerSupervisor` stops issuing new `XREADGROUP` calls; consumer tasks exit after current event.
- `ListenerManager.stop()` stops every `DockerMonitor` in parallel.
- Each `DockerMonitor`: set thread shutdown flag, wait up to 5s for thread exit, close Docker client.
- In-flight LangGraph invocations get 10s grace, then cancelled.
- Unacked events remain in the pending entries list — next worker instance picks them up.

## Testing

### Unit (no Docker, no Redis)

- `tests/unit/listener/test_dedup.py` — add events, verify 60s window, different containers don't collide, cache cleanup works.
- `tests/unit/listener/test_container_filter.py` — `monitor_all_containers=true` always passes; `false` honors whitelist.
- `tests/unit/listener/test_manager.py` — mock DB, mock `DockerMonitor`, verify spawn/stop logic on host diffs.
- `tests/unit/worker/test_supervisor.py` — mock DB, verify per-tenant task spawn/cancel.
- `tests/unit/worker/test_process_event.py` — mock orchestrator, verify DB insert + ack behavior on both success and `NotImplementedError`.

### Integration (Docker-in-Docker + real Redis)

- Spin up a test container, send it SIGKILL, assert event reaches Redis stream `crashes:{tenant_id}` within 3s with correct payload.
- Assert `docker_hosts.status` transitions to `"connected"` on startup and `"reconnecting"` when the Docker daemon is paused mid-session.
- Dedup: rapid-fire kill three containers within 1s, assert exactly one published event per container (one per `(host, container)` pair).

### End-to-end ("Phase 1 done" gate)

- `docker compose up` → full stack.
- From another shell on the monitored host: `docker run --rm busybox exit 1`.
- Assert: one event lands in Redis stream, worker dequeues it, writes a pending `CrashEvent` row, and the orchestrator's `analyze_crash` node raises `NotImplementedError` (expected — Phase 2 fills it in).

## Dependencies

Already in `requirements.txt`:
- `docker` — Docker SDK
- `redis[hiredis]` — Redis client
- `sqlalchemy[asyncio]`, `asyncpg` — DB
- `langgraph` — orchestrator

No new dependencies for this phase.

## Out of scope for this spec (deferred)

- Agent-mode host support (covered by item #26).
- Hot config updates to existing monitors (e.g., container filter changes while running) — currently requires toggle `is_active` off and back on.
- Multi-worker replica coordination.
- Metrics/observability beyond status column updates. Prometheus counters added opportunistically in `src/services/metrics.py` but not a deliverable of this spec.
- The LangGraph orchestrator node implementations themselves (items #4, #5, #6).

## Acceptance criteria

Phase 1 is done when:

1. A `die` event on a registered TCP host produces exactly one Redis stream message within 3 seconds.
2. The message is successfully consumed by the worker and invokes `crash_workflow.ainvoke()`.
3. `docker_hosts.status` reflects monitor health in real time.
4. Killing a Docker host connection triggers `reconnecting` status and automatic recovery when the host returns.
5. All unit and integration tests defined above pass.
6. Graceful SIGTERM shutdown completes within 15 seconds.
