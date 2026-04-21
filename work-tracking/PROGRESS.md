# DockerSentinel — Work Tracker

> **Last updated:** 2026-04-15
> **Current phase:** Skeleton complete, moving to agent implementation

---

## What's Done (Completed)

### Backend Skeleton
- [x] FastAPI app factory with middleware (CORS, metrics, auth)
- [x] SQLAlchemy async models with TenantMixin (User, Tenant, DockerHost, CrashEvent, NotificationConfig, EscalationRule, ApiKey)
- [x] Pydantic schemas for all models (request/response)
- [x] Service layer: auth, tenant, crash_event, api_key, database, redis_stream, metrics
- [x] API routers: health, crash_events, api_keys, notifications, escalations, websocket
- [x] LangGraph orchestrator graph with state machine and conditional edges (`graph.py`, `state.py`)
- [x] Alembic migration setup
- [x] Docker Compose (dev + prod) with PostgreSQL, Redis, Qdrant
- [x] GitHub Actions CI pipeline
- [x] Email template (Jinja2 `crash_email.html`)
- [x] Pytest + pytest-asyncio test suite scaffolding

### Frontend (Fully Implemented)
- [x] Next.js 15 + React 19 + Shadcn/ui + Tailwind CSS
- [x] Auth pages (login with GitHub/Google buttons)
- [x] Dashboard pages (overview, crash detail)
- [x] Hosts management page
- [x] Settings page (notifications, escalations, API keys)
- [x] Onboarding flow
- [x] Sidebar + Header navigation
- [x] API client, auth helpers, React hooks (useAuth, useCrashes, useWebSocket)

---

## What's NOT Done (All NotImplementedError Placeholders)

### Phase 1 — Core Pipeline (Do This First)
These form the end-to-end crash detection pipeline. Without these, nothing works.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 1 | `src/listener/docker_monitor.py` | Docker event listener (connect via Docker SDK, stream die/oom/kill events) | ✅ **Done** |
| 2 | `src/listener/manager.py` | Listener manager (sync listeners from DB, start/stop monitors) | ✅ **Done** |
| 3 | `src/worker/main.py` | Crash event consumer (poll Redis streams, invoke LangGraph workflow) | ✅ **Done** |
| 4 | `src/orchestrator/nodes.py` → `analyze_crash` | Fix Agent call (Qdrant cache check + LLM analysis) | **Critical** |
| 5 | `src/orchestrator/nodes.py` → `attempt_restart` | Docker SDK restart container | **Critical** |
| 6 | `src/orchestrator/nodes.py` → `log_event` | Persist crash event result to PostgreSQL | **Critical** |

### Phase 2 — Agents & Notifications
Once the pipeline works, add intelligence and alerting.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 7 | `src/agents/fix_agent.py` | LLM crash analysis (Claude Haiku + structured output, Qdrant cache) | **High** |
| 8 | `src/agents/slack_agent.py` | Slack webhook notification (Block Kit format) | **High** |
| 9 | `src/agents/email_agent.py` | Email notification (Jinja2 template + SMTP) | **High** |
| 10 | `src/agents/call_agent.py` | Twilio voice call escalation (LLM script generation + TwiML) | **Medium** |
| 11 | `src/agents/dashboard_agent.py` | AI summary generation for dashboard | **Medium** |
| 12 | `src/orchestrator/nodes.py` → `notify_slack` | Wire Slack agent into orchestrator | **High** |
| 13 | `src/orchestrator/nodes.py` → `send_email` | Wire Email agent into orchestrator | **High** |
| 14 | `src/orchestrator/nodes.py` → `make_call` | Wire Call agent into orchestrator | **Medium** |

### Phase 3 — RAG & Memory
Vector search for crash deduplication and past fix lookups.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 15 | `src/services/crash_memory.py` → `search()` | Qdrant similarity search (embed crash logs, find similar past crashes) | **High** |
| 16 | `src/services/crash_memory.py` → `store()` | Qdrant storage (embed + store crash analysis results) | **High** |

### Phase 4 — Auth & API Completions
OAuth flows and remaining API endpoints.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 17 | `src/api/routers/auth.py` | GitHub OAuth login + callback | **High** |
| 18 | `src/api/routers/auth.py` | Google OAuth login + callback | **High** |
| 19 | `src/api/routers/tenants.py` → `invite_member()` | Email invitation + pending user record | **Medium** |
| 20 | `src/api/routers/docker_hosts.py` → `list_containers()` | Connect to Docker host, list containers | **Medium** |
| 21 | `src/services/docker_host_service.py` → test connection | Docker SDK connection test | **Medium** |
| 22 | `src/services/notification_service.py` → `test_notification()` | Test Slack/Email/Twilio channel | **Medium** |

### Phase 5 — Dashboard Intelligence
AI-powered dashboard metrics and insights.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 23 | `src/api/routers/dashboard.py` → `get_summary()` | AI summary via Dashboard Agent | **Low** |
| 24 | `src/api/routers/dashboard.py` → `get_metrics()` | Query crash_events for MTTR, cache hit rate, restart success | **Low** |
| 25 | `src/api/routers/dashboard.py` → `get_timeline()` | Aggregate crashes by hour/day | **Low** |

### Phase 6 — Agent Container
Standalone agent for customer-hosted Docker environments.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 26 | `src/agent_container/main.py` | Local Docker event stream + WebSocket relay to API server | **Low** |

---

## Daily Log

### 2026-04-15
- **Status:** Reviewed entire project state. Skeleton is 100% complete.
- **What was done:** Created this work tracker. Full audit of all 26 placeholder items.
- **Pick up from here:** Start with **Phase 1, Item #1** — `src/listener/docker_monitor.py` (Docker event listener). This is the entry point of the entire crash pipeline.

### 2026-04-21 (Today)
- **Status:** Phase 1 items #1, #2, #3 complete — crash ingestion pipeline is built.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-21-crash-ingestion-pipeline-design.md`
  - Wrote 14-task implementation plan: `docs/superpowers/plans/2026-04-21-crash-ingestion-pipeline.md`
  - Extended `CrashEventCreate` schema with `event_type`, `event_timestamp`
  - Built `DockerMonitor`: thread/async bridge, dedup (60s window), container filter, logs capture, exponential-backoff reconnect, DB status writes
  - Built `ListenerManager`: 30s DB-sync poll loop, spawn/stop diff, TLS config from DB, parallel graceful shutdown
  - Built `Worker`: `TenantConsumerSupervisor` (per-tenant consumer tasks), `_process_event` (DB insert + LangGraph handoff), `main()` with signal handlers (SIGTERM/SIGINT + Windows fallback)
  - 30 unit tests passing; 12 commits on branch `feat/crash-ingestion-pipeline` (ready to merge after smoke test)
- **Pick up from here:** **Phase 1 items #4, #5, #6** — LangGraph orchestrator nodes (`analyze_crash`, `attempt_restart`, `log_event`) in `src/orchestrator/nodes.py`. With the pipeline delivering events, we can now wire real analysis. Note: `analyze_crash` depends on Fix Agent (#7) and Qdrant cache (#15, #16) — consider sequencing Phase 2/3 work first, or stub the LLM call initially.

---

## Quick Reference

**Run the stack:**
```bash
docker compose up                         # full stack
uvicorn src.api.app:create_app --factory --reload --port 8000  # API only
python -m src.worker.main                 # worker only
cd frontend && npm run dev                # frontend only
```

**Test & lint:**
```bash
pytest
ruff check src/ tests/
```
