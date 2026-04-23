# DockerSentinel — Work Tracker

> **Last updated:** 2026-04-24
> **Current phase:** Full-stack product. Crashes on a registered Docker host flow through the full loop: detect → LLM-analyze (with Qdrant cache) → conditionally restart → Slack + Email notifications → persist to DB. **Frontend completely redesigned** with AI-aesthetic dark theme, Framer Motion micro-interactions, and live WebSocket feed. Dashboard aggregate endpoints live. Remaining scope: Twilio voice, observability polish, agent container.

**Test suite:** 153 tests passing (142 prior + 8 dashboard router + 3 ws-token).

**Phase scoreboard:**

| Phase | Items | Status |
|---|---|---|
| 1 — Core pipeline | #1–6 (listener, manager, worker, analyze_crash, attempt_restart, log_event) | ✅ Shipped |
| 2 — Intelligence + notifications | #7 Fix Agent, #8 SlackAgent, #9 EmailAgent, #12 notify_slack, #13 send_email | ✅ Shipped |
| 2 — Deferred | #10 CallAgent / #14 make_call (Twilio), #11 DashboardAgent | Pending |
| 3 — RAG memory | #15 find_similar, #16 store (Qdrant + fastembed) | ✅ Shipped |
| 4 — Auth & API completions | #17 Google OAuth ✅; #19–22 host containers, member invite, notification test | Partially shipped |
| 5 — Dashboard AI | #23–25 (summary, metrics, timeline endpoints) | ✅ Shipped (SQL aggregates; AI summary composed client-side) |
| 6 — Agent container | #26 (customer-host agent via WebSocket) | Skeleton only |
| 7 — Frontend redesign | Full bug-fix + visual polish with live data across 11 pages | ✅ Shipped |

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
| 4 | `src/orchestrator/nodes.py` → `analyze_crash` | Fix Agent call (Qdrant cache check + LLM analysis) | ✅ **Done** (Fix Agent wired; Qdrant still stubbed — Phase 3) |
| 5 | `src/orchestrator/nodes.py` → `attempt_restart` | Docker SDK restart container | ✅ **Done** |
| 6 | `src/orchestrator/nodes.py` → `log_event` | Persist crash event result to PostgreSQL | ✅ **Done** |

### Phase 2 — Agents & Notifications
Once the pipeline works, add intelligence and alerting.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 7 | `src/agents/fix_agent.py` | LLM crash analysis (OpenAI `gpt-4o-mini` primary + `gpt-4o` fallback, structured output) | ✅ **Done** (Qdrant cache uses Phase 2 stubs — Phase 3 swaps in real Qdrant) |
| 8 | `src/agents/slack_agent.py` | Slack webhook notification (Block Kit format) | ✅ **Done** |
| 9 | `src/agents/email_agent.py` | Email notification (Jinja2 template + Gmail SMTP via aiosmtplib) | ✅ **Done** |
| 10 | `src/agents/call_agent.py` | Twilio voice call escalation (LLM script generation + TwiML) | **Medium** |
| 11 | `src/agents/dashboard_agent.py` | AI summary generation for dashboard | **Medium** |
| 12 | `src/orchestrator/nodes.py` → `notify_slack` | Wire Slack agent into orchestrator | ✅ **Done** |
| 13 | `src/orchestrator/nodes.py` → `send_email` | Wire Email agent into orchestrator | ✅ **Done** |
| 14 | `src/orchestrator/nodes.py` → `make_call` | Wire Call agent into orchestrator | **Medium** |

### Phase 3 — RAG & Memory
Vector search for crash deduplication and past fix lookups.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 15 | `src/services/crash_memory.py` → `find_similar()` | Qdrant similarity search (fastembed + bge-small, tenant-filtered) | ✅ **Done** |
| 16 | `src/services/crash_memory.py` → `store()` | Qdrant upsert with tenant_id + analysis + metadata payload | ✅ **Done** |

### Phase 4 — Auth & API Completions
OAuth flows and remaining API endpoints.

| # | File | What to Implement | Priority |
|---|------|-------------------|----------|
| 17 | `src/api/routers/auth.py` | Google OAuth login + callback (Authlib OIDC + HttpOnly cookies) | ✅ **Done** |
| 18 | `src/api/routers/auth.py` | GitHub OAuth login + callback | 🗑️ **Removed** (same pattern available if re-added) |
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
- **Status:** ✅ **Phase 1 items #1, #2, #3 shipped** — crash ingestion pipeline is built, tested, and merged to `master`.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-21-crash-ingestion-pipeline-design.md`
  - Wrote 14-task implementation plan: `docs/superpowers/plans/2026-04-21-crash-ingestion-pipeline.md`
  - Extended `CrashEventCreate` schema with `event_type`, `event_timestamp`
  - Built `DockerMonitor`: thread/async bridge, dedup (60s window), container filter, logs capture, exponential-backoff reconnect, DB status writes
  - Built `ListenerManager`: 30s DB-sync poll loop, spawn/stop diff, TLS config from DB, parallel graceful shutdown
  - Built `Worker`: `TenantConsumerSupervisor` (per-tenant consumer tasks), `_process_event` (DB insert + LangGraph handoff), `main()` with signal handlers (SIGTERM/SIGINT + Windows fallback)
  - 32 tests passing (30 unit + 2 schema)
  - **End-to-end smoke test verified**: real `busybox exit 1` crash → Redis stream → worker consumer → LangGraph invocation. Also captured unrelated containers dying on the host (celery_beat, pgbouncer, fastapi-listener-local) — proves `monitor_all_containers` path works.
  - Merged `feat/crash-ingestion-pipeline` → `master` via `--no-ff` (merge commit `e02271e`). Branch deleted.
- **Known deferred trade-offs (document in case they bite later):**
  - Redis `XACK` fires on read (in `src/services/redis_stream.py`) rather than after successful processing. At-most-once for processing failures. Fix when Phase 2 lands real orchestrator logic.
  - TLS temp files in `ListenerManager._build_tls_config` are `delete=False`; they leak if a TLS-enabled host is repeatedly toggled. Fine at portfolio scale.
  - The per-monitor thread pushes to `asyncio.Queue` via `run_coroutine_threadsafe` without checking the returned Future — if the 1000-item queue fills, producer blocks silently. Never happens at portfolio scale.
- **Pick up from here:** **Phase 1 items #4, #5, #6** — LangGraph orchestrator nodes (`analyze_crash`, `attempt_restart`, `log_event`) in `src/orchestrator/nodes.py`.
  - The pipeline is delivering events to `crash_workflow.ainvoke()` right now and hitting `NotImplementedError` in the first node.
  - **Suggested sequence:**
    1. `log_event` first (trivial — persist analysis results to the existing `CrashEvent` row). Gets the terminal node working so other paths have somewhere to terminate.
    2. `attempt_restart` next (Docker SDK `container.restart()` with status tracking). Pure Docker, no LLM.
    3. `analyze_crash` last — depends on Fix Agent (#7, Claude Haiku) and Qdrant cache (#15, #16). Either stub the LLM to return a canned `CrashAnalysis`, OR jump ahead to build Fix Agent + Qdrant first.
  - **Recommendation:** Do `log_event` + `attempt_restart` first (they complete the non-LLM parts of the state machine), then pivot to Phase 2 Fix Agent so `analyze_crash` has a real backend.

### 2026-04-21 (Continued — afternoon session)
- **Status:** ✅ **Phase 1 items #5 and #6 shipped**; #4 stubbed (Fix Agent body replaces it in Phase 2).
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-21-orchestrator-nodes-design.md`
  - Wrote 10-task implementation plan: `docs/superpowers/plans/2026-04-21-orchestrator-nodes.md`
  - Extracted TLS config helper to `src/listener/_tls.py`; `ListenerManager` delegates
  - Updated `CrashState` schema: added `crash_event_id`, `docker_host_id`; made `restart_success` nullable
  - Updated `worker._process_event` to build the full state dict (matches the new schema)
  - Stubbed `analyze_crash` (returns canned CrashAnalysis with `restart_likely_fixes=True` so the state machine stays live)
  - Implemented `attempt_restart` (stateless fresh Docker client via `asyncio.to_thread`; handles `NotFound`, `APIError`, missing host)
  - Implemented `log_event` (UPDATE pending CrashEvent row with all analysis + action fields, `resolved_at = now()`)
  - **End-to-end smoke test verified** on 2026-04-22: real crash → fully populated CrashEvent row (`restart_attempted=t, restart_success=t, root_cause, severity, resolved_at` all set)
  - 46 tests passing (44 unit + 2 schema); 2 review-fix commits after initial review caught a critical routing bug (`check_restart_result` → `notify_slack` NotImplementedError) and a semantic inconsistency in `attempt_restart` early-return branches — both fixed
  - Merged `feat/orchestrator-nodes` → `master` via `--no-ff` (merge commit `85e1b71`). Branch deleted.
- **Pick up from here:** **Phase 2 Fix Agent (item #7)** — replace the `analyze_crash` stub body with real Claude Haiku calls. Then Qdrant cache (items #15, #16) so repeat crashes don't burn LLM tokens. After Fix Agent: notification agents (#8–11) — SlackAgent, EmailAgent, CallAgent.
  - **Suggested sequence for next session:**
    1. Design Fix Agent + Qdrant together (they're tightly coupled — cache check happens before LLM call).
    2. Build Fix Agent with a stubbed Qdrant first (always miss → always call LLM). Prove end-to-end LLM invocation.
    3. Add real Qdrant embeddings + similarity search.
  - **Pre-work needed:** Anthropic API key in `.env` (currently has `your_anthropic_api_key` placeholder).

### 2026-04-22 (Today)
- **Status:** ✅ **Phase 2 item #7 shipped** — Fix Agent calling OpenAI with structured output. Phase 1 item #4 (`analyze_crash`) is now fully wired end-to-end with real LLM analysis.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-22-fix-agent-design.md`
  - Wrote 8-task plan: `docs/superpowers/plans/2026-04-22-fix-agent.md`
  - Replaced `CrashMemory` `NotImplementedError` with Phase 2 stubs (find_similar → None, store → pass)
  - Added `src/agents/_prompts.py` — pure prompt builder with 200-line log truncation
  - Built `FixAgent` (singleton + LangChain chain: gpt-4o-mini primary + gpt-4o fallback, `with_structured_output(CrashAnalysis)`, minimal-fallback analysis on both-fail)
  - Rewired `analyze_crash` to call `get_fix_agent().analyze(...)`
  - Updated end-to-end workflow test to patch `get_fix_agent`
  - **Direction change:** Project switched to OpenAI as main LLM (previously planned Anthropic Claude). OpenAI API key already in `.env`.
  - 58 unit tests passing (up from 46), all LLM mocked in CI. One review-fix commit (AsyncMock in conftest for tighter sync/async regression detection).
- **Known deferred items:**
  - Qdrant cache is still stubbed — Phase 3 will embed logs with `text-embedding-3-small` and upsert to a Qdrant collection.
  - `CrashEvent.llm_provider` and `llm_latency_ms` columns still NULL — minor follow-up task in a later session.
  - No Prometheus metrics for LLM failures yet — add with observability work.
- **Pick up from here:** **Phase 3 Qdrant memory (items #15, #16)** — replace `CrashMemory` stubs with real vector similarity search. Suggested sequence:
  1. Design Qdrant collection schema (vector size, payload fields, distance metric).
  2. Build `CrashMemory.store()` first (easier — just embed + upsert).
  3. Build `CrashMemory.find_similar()` with the 0.92 threshold.
  4. Tune the threshold against real crash logs captured in `crash_events` table.
  - **Alternative:** Jump to Phase 2 notification agents (#8–11) first — SlackAgent, EmailAgent, CallAgent — to complete the user-visible workflow. Qdrant is pure cost optimization; notifications are user-facing.

### 2026-04-22 (Continued — evening session)
- **Status:** ✅ **Phase 3 items #15 and #16 shipped** — Qdrant semantic cache live. Repeat crashes reuse cached `CrashAnalysis` without calling OpenAI.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-22-qdrant-memory-design.md`
  - Wrote 7-task plan: `docs/superpowers/plans/2026-04-22-qdrant-memory.md`
  - Added `fastembed>=0.3.0` dependency (ONNX-based open embeddings, no PyTorch)
  - Implemented `CrashMemory` with real `QdrantClient` + `TextEmbedding("BAAI/bge-small-en-v1.5")`, single shared `crash_history` collection, cosine distance, tenant filtering via payload `FieldCondition`, 0.92 default threshold
  - Thread-safe lazy-init via `threading.Lock` (prevents double model-load under concurrent access)
  - Reserved-key guard on store payload — metadata can't overwrite `tenant_id`/`analysis`/`created_at` (multi-tenant isolation hardening)
  - All failures swallowed so LLM path is always reachable
  - Threaded `tenant_id` through `FixAgent.analyze(crash_event, tenant_id)` and `analyze_crash` node
  - Added `_build_embedding_text` helper: `"<image> | exit=<code> | <logs>"` for stronger similarity signal
  - Deleted obsolete `test_crash_memory_stubs.py`; 14 new tests in `tests/unit/services/test_crash_memory.py` (12 planned + 2 hardening tests)
  - 76 unit tests passing
- **Known deferred items:**
  - Threshold tuning — 0.92 is a starting guess for bge-small; revisit after real crash data accumulates.
  - No TTL / eviction — collection grows forever (fine at portfolio scale).
  - No Qdrant payload index on `tenant_id` — at scale, the filter becomes a full-scan. Add `create_payload_index(field_name="tenant_id", field_schema="keyword")` when volume warrants.
  - Embedding-text format is hardcoded in `_build_embedding_text`; changing it requires rebuilding the collection.
  - `model_version` not in payload — if Fix Agent prompts/models change, old cache entries remain.
  - Pre-warming the fastembed model in Docker image build for faster first-crash latency.
- **Pick up from here:** **Phase 2 notification agents (items #8–11)** — SlackAgent, EmailAgent, CallAgent, DashboardAgent. Unlocks the `restart_likely_fixes=False → notify_slack` path currently routed to `log`. User-visible value (a real Slack message on crash is a great demo). After notifications: observability/metrics or multi-worker scaling.

### 2026-04-23 (Continued — notification agents)
- **Status:** ✅ **Phase 2 items #8, #9, #12, #13 shipped.** Slack + Email notifications live. Restored False → notify_slack edges in the orchestrator graph.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-23-notification-agents-design.md`
  - Wrote 9-task plan: `docs/superpowers/plans/2026-04-23-notification-agents.md`
  - Added `aiosmtplib>=3.0.0` dep; new SMTP settings (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`)
  - `SlackAgent.notify` — httpx POST to per-tenant webhook, Block Kit payload, severity→emoji mapping, truncates to 3 suggestions
  - `EmailAgent.send` — Jinja2 renders `crash_email.html`, aiosmtplib sends over Gmail STARTTLS; template path anchored to `__file__` (CWD-safe)
  - `get_notification_config(tenant_id, channel)` helper in `notification_service.py` — returns enabled config row or None
  - `notify_slack` / `send_email` orchestrator nodes — per-tenant config lookup, outer exception guard, graph never dies in a notification node
  - Restored `should_restart` False → `notify_slack`; `check_restart_result` non-True → `notify_slack`
  - Updated graph mappings: `{"attempt_restart": "restart", "notify_slack": "slack"}` on `analyze`; `{"log": "log", "notify_slack": "slack"}` on `restart`
  - Made `make_call` a logged no-op (was `NotImplementedError`) so the multi-crash path is safe if someone later starts populating `recent_crash_count`
  - 31 new unit tests (8 Slack + 6 Email + 5 service helper + 10 node + 2 E2E); 107 tests total
  - One review-fix cycle: template-path CWD bug + make_call NotImplementedError latent bug
- **Known deferred items:**
  - **CallAgent + Twilio** (item #10) + `make_call` node (#14) — voice escalation. Requires Twilio trial + phone number.
  - **DashboardAgent** (item #11) — separate dashboard-UI concern, not crash-notification.
  - **Retry / backoff** on Slack 429 and SMTP timeouts.
  - **Multi-recipient email** — per-tenant single `to` address only.
  - **Container-owner routing via Docker labels** — listener doesn't capture labels yet.
  - **Rich Slack interactivity** (buttons, threads).
  - **Notification deduplication** — every crash notifies even if Qdrant cache already saw it.
- **Pick up from here:** Good candidates for the next session:
  - **CallAgent + make_call wiring (items #10, #14)** — closes out Phase 2's escalation path. Twilio trial account required.
  - **DashboardAgent (item #11)** + wire into a dashboard API endpoint — useful dashboard UI demo.
  - **Observability & metrics** — populate `llm_provider`/`llm_latency_ms` columns, add Prometheus counters for notification success/failure, tune the Qdrant threshold against real crash data.
  - **Frontend polish** — the Next.js dashboard is already scaffolded; wire it to the API and show live crashes, analyses, and notifications.

### 2026-04-23 (Continued — Google OAuth)
- **Status:** ✅ **Phase 4 item #17 shipped.** Google OIDC sign-in working end-to-end with production-grade cookie auth. GitHub routes removed.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-23-google-oauth-design.md`
  - Wrote 10-task plan: `docs/superpowers/plans/2026-04-23-google-oauth.md`
  - Added `itsdangerous` dep + `SessionMiddleware` (Starlette) for Authlib state+nonce storage
  - `src/services/oauth_client.py` — module-level Authlib `OAuth` registry with Google OIDC discovery URL
  - `src/services/auth_cookies.py` — centralized `HttpOnly` / `SameSite=Lax` cookie helpers; refresh-token scoped to `/api/v1/auth`; `Secure` only in production
  - `get_current_user` now reads `access_token` cookie first, falls back to `Authorization: Bearer` for programmatic access; raises **401** (not 403)
  - Rewrote `auth.py` router: Google `/google` + `/google/callback` (Authlib-handled state + nonce + JWT verification), cookie-based `/refresh` (rotates both tokens) + `/logout` (clears cookies), `/me` now cookie-based
  - Removed GitHub routes + `TokenRefresh` schema
  - Frontend: Google-only login with brand "G" logo SVG, simplified callback page (no token-from-URL parsing), cookie-based API client with transparent 401→refresh→retry, `useAuth` hook calls `/me` on mount
  - Updated legacy `tests/test_api/` to expect 401 instead of 403
  - 20 new unit tests (4 cookies + 2 oauth_client + 5 deps + 9 router). 142 tests total.
  - **Note:** `use-websocket.ts` no longer passes a token query param — WebSocket cookie auth will need attention when dashboard wiring lands.
- **Known deferred items:**
  - Refresh-token blacklist + reuse detection.
  - Email whitelist (anyone with a Google account can auto-provision a tenant).
  - Logout-everywhere (invalidating all refresh tokens for a user).
  - Prometheus counters for auth success/failure.
  - PKCE extension (overkill for confidential client with server-side secret).
  - Production OAuth consent screen publishing + domain-verified redirect URIs.
  - WebSocket auth (cookies flow on handshake, but the current `use-websocket.ts` removed token handling — verify on dashboard-wiring session).
- **Pre-work for next user who runs the app:** follow the Google Cloud Console setup in `docs/superpowers/specs/2026-04-23-google-oauth-design.md` §Configuration. Populate `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` in `.env`. Add `http://localhost:8000/api/v1/auth/google/callback` to the OAuth client's authorized redirect URIs.
- **Pick up from here:** Good candidates for the next session:
  - **Dashboard wiring (Phase 5 items #23–25)** — `/api/v1/dashboard/{summary,metrics,timeline}` endpoints + Next.js pages consuming live crash data. Resolves the WebSocket auth question too.
  - **CallAgent + Twilio (items #10, #14)** — voice escalation.
  - **Observability & metrics** — Prometheus counters for notifications, LLM failures, auth events.
  - **Agent container (Phase 6 item #26)** — customer-hosted agent via WebSocket.

### 2026-04-24 (Frontend redesign + backend gap-fill)
- **Status:** ✅ **Phase 5 items #23, #24, #25 shipped** (dashboard aggregate endpoints). ✅ **Frontend completely redesigned** on `feat/frontend-redesign` branch — AI-aesthetic dark-first theme, Framer Motion micro-interactions, Recharts, live WebSocket feed, 11 pages rebuilt from bare placeholders into production-grade UI. Phase 4 item #22 (`test_notification`) surfaced in UI but backend is still pre-existing.
- **What was done (backend):**
  - `src/api/routers/dashboard.py` — replaced all three `NotImplementedError`s with real tenant-scoped SQL aggregations over `crash_events`:
    - `/summary` → crashes_24h / restarts_24h / cache_hit_rate / active_hosts.
    - `/metrics?period=24h|7d|30d` → MTTR (with period-over-period delta), severity/category breakdowns.
    - `/timeline?period=...` → Python-side gap-filled hourly/daily bucket series.
  - `src/schemas/dashboard.py` — new Pydantic response models (`DashboardSummary`, `DashboardMetrics`, `DashboardTimeline`, `TimelinePoint`).
  - `POST /api/v1/auth/ws-token` — short-lived (60s) WS-type JWT minted from the authenticated cookie; used by the frontend since cookies don't flow reliably to the WebSocket handshake.
  - 8 new dashboard router tests + 3 new ws-token tests. Total **153 tests passing**.
- **What was done (frontend — feat/frontend-redesign branch, 16 commits):**
  - **Design system:** dark-first OKLch palette (`globals.css`), Geist Mono via `next/font/google`, next-themes with `defaultTheme="dark"`, Sonner toaster, new severity/gradient/glow tokens. **Dep bumps:** `lucide-react ^0.474.0` (was pre-rename 1.8.0 — nav icons couldn't import), `framer-motion ^11.18.0`, `recharts ^2.15.0`, `date-fns ^4.1.0`.
  - **Motion primitives** in `components/ui/motion/`: `<Shimmer>` (skeleton sweep), `<GlowCard>` (mouse-follow radial spotlight, tints cyan/violet/magenta), `<AnimatedGradient>` (gradient-clip text), `<PulseDot>` (live/connecting/offline dot).
  - **App shell:** `<MeshBackground>` (drifting radial blobs + grid), `<PageTransition>` (AnimatePresence fade-slide on pathname change), `<Sidebar>` (AnimatedGradient wordmark + shared-element nav glow via `layoutId`), `<Header>` (breadcrumb + PulseDot WS status + theme toggle + avatar dropdown with `HeaderSkeleton` during auth load).
  - **Bug fixes (all from pre-redesign audit):**
    - **Bug 1** — `src/proxy.ts` (renamed from `middleware.ts` per Next 16): auth gate redirects unauth dashboard routes → `/login`, bounces authed `/login` → `/`.
    - **Bug 2** — `nav-links.tsx` now imports Lucide icons as components (was storing string literal names — nothing rendered).
    - **Bug 3** — `use-websocket.ts` rewritten as module-level singleton with refCount sharing, token-refresh every 55s, heartbeat every 25s, exponential-backoff reconnect (1s→30s cap), `POST /auth/ws-token` → `?token=` URL param.
    - **Bug 4** — `/crashes/[id]` uses `use(params)` (Next 16 made `params` a Promise).
    - **Bug 5** — `HeaderSkeleton` renders while `useAuth().loading`.
    - **Bug 6** — `useAuth` now exposes `error` field; `getMe()` in `lib/auth.ts` returns `null` on 401, throws on 5xx.
    - **Bug 7** — `useCrashes` wired into `/crashes` page (was unused).
  - **Pages redesigned (11 total):**
    - `/login` — glass card, mesh bg, AnimatedGradient wordmark, Google button with violet glow hover.
    - `/callback` — three counter-rotating orbital rings.
    - `/` dashboard — 4 `<GlowCard>` metric tiles with Framer Motion count-up + stagger, AI Summary card (narrative composed from live metrics), Recharts `<AreaChart>` timeline with brand-gradient fills, period selector (24h/7d/30d) with shared `layoutId` glow pill, loading skeleton, error retry.
    - `/crashes` — filter bar, Shadcn Table with severity badges + cache/status indicators, **live WebSocket prepends new crashes with severity flash animation** (filter-guarded, per-id timer Map prevents burst leak), client-side search.
    - `/crashes/[id]` — shared-element hero via `layoutId="crash-hero-${id}"`, 4-tab layout (Logs / AI Analysis / Timeline / Actions), Geist Mono metadata sidecar, 404 empty state.
    - `/hosts` — grid of `<GlowCard>`s with `<PulseDot>`, deterministic per-host sparklines (FNV-1a hashed seed), connection-mode badges, test + delete actions with confirm dialog.
    - `/hosts/new` — 3-step animated wizard (mode → details → review) with progress bar, `AnimatePresence` step transitions.
    - `/settings` hub — 4-GlowCard grid linking to sub-sections.
    - `/settings/api-keys` — table + two-phase generate dialog (form → copy-once key view with pulse-cyan glow + clipboard). Secret cleared on dialog close.
    - `/settings/members` — list with gradient-avatar initials + invite dialog (backend still 501, body shows coming-soon EmptyState).
    - `/settings/notifications` — per-channel GlowCard with enable toggle + test button, optimistic toggle with rollback + sync-effect.
    - `/settings/escalations` — rule list + side-Sheet create/edit form, condition summary rendered as readable sentence.
    - `/onboarding` — 3-step wizard (Add Host → Configure Alerts → You're Ready) using real `createHost` + `updateNotificationConfig` mutations; success hero with Go-to-Dashboard + Copy-test-crash-command CTAs.
    - `/not-found` + `/error` — polished glass boundaries with MeshBackground.
  - **New hooks:** `use-dashboard` (summary/metrics/timeline), `use-crash` (single fetch), `use-docker-hosts`, `use-api-keys`, `use-members`, `use-notification-configs`, `use-escalation-rules`. All use **generation-counter pattern** to guard against out-of-order refresh responses (caught in T10 review and applied to all subsequent hooks).
- **Review / quality cycle:** Followed superpowers subagent-driven-development for every task. Each task went through spec-compliance review + code-quality review, with a fix commit per review finding. Notable fixes:
  - Dashboard: surfaced metrics/timeline errors that were silently swallowed; aligned Crashes tile label/value/delta when period changes.
  - Crashes: filter-guarded WS prepend; per-id Map for flash timers (burst-safe); layoutId collision rename.
  - Hosts: generation-counter race fix on `useDockerHosts`.
  - Settings: API-key secret cleared explicitly on close; child-card state sync effects; Sheet close-while-saving guard; custom-days validation before POST.
- **Known deferred items:**
  - Full WCAG audit (beyond Shadcn/base-ui's built-in focus + aria).
  - Light-mode polish (exists and functional, dark is primary).
  - Virtualized tables (>1000 rows).
  - Global cmd-k search (slot reserved in header; implementation later).
  - Drag-to-reorder on escalation rules (Sheet editor handles single rule; ordering later).
  - `invite_member` backend is still 501 — UI shell built, mutation returns coming-soon EmptyState.
  - `list_containers` backend — no page consumes it yet.
  - Frontend test harness (Vitest / Playwright) — manual visual verification only so far.
  - Host-card sparklines are deterministic-placeholder (seeded by `host.id`); real per-host crash-series endpoint is future work.
  - `CrashEvent.llm_provider` and `llm_latency_ms` still NULL in rows produced before the columns were wired up.
- **Pick up from here:** Good candidates:
  - **CallAgent + Twilio (items #10, #14)** — voice escalation + `/settings/notifications` voice card is ready to light up.
  - **Observability & metrics** — Prometheus counters, populate LLM provider/latency columns, tune Qdrant threshold.
  - **Real per-host sparkline endpoint** — swap deterministic placeholder for `GET /api/v1/hosts/{id}/recent-activity`.
  - **`invite_member` implementation (Phase 4 item #19)** — email invitation + pending-user record. UI ready.
  - **Agent container (Phase 6 item #26)** — customer-hosted agent via WebSocket. WS token endpoint + `use-websocket` singleton are ready for agent-side consumption.
  - **Frontend test harness** — Vitest + React Testing Library for hooks, Playwright for critical flows (login, trigger crash, view in dashboard).

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
