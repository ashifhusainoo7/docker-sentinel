# DockerSentinel

[![CI](https://github.com/ashifhusainoo7/docker-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/ashifhusainoo7/docker-sentinel/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-165%20passing-brightgreen.svg)](#-testing)
[![Code style: ruff](https://img.shields.io/badge/lint-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A multi-tenant SaaS platform that monitors Docker container crashes, analyzes the root cause with an LLM, attempts automated recovery, and notifies your team via Slack and email — all with a Qdrant-backed semantic cache so repeat crashes don't burn LLM tokens.

**Current capabilities (2026-04-23):**

- Detects `die` / `oom` / `kill` events on registered Docker hosts over TCP or the local named pipe.
- Filters + dedups events (60 s per-container window).
- Publishes per-tenant crash streams to Redis.
- LangGraph orchestrates analysis → optional restart → notifications → persisted `CrashEvent` row.
- LLM analysis via OpenAI `gpt-4o-mini` with `gpt-4o` fallback, structured output into a `CrashAnalysis` Pydantic model.
- Qdrant semantic cache (fastembed + `bge-small-en-v1.5`, 384-dim cosine) with per-tenant isolation; repeat crashes skip the LLM entirely.
- Slack notifications (Block Kit) and HTML email notifications (Gmail SMTP via `aiosmtplib`).
- Per-tenant `NotificationConfig` with `is_enabled` mute switch.

---

## Screenshots

> 📸 _Screenshots coming soon._ Drop images in `docs/images/` and they'll render below.

<!--
| Live crash feed | Crash detail + LLM analysis |
| --------------- | --------------------------- |
| ![Dashboard live feed](docs/images/dashboard.png) | ![Crash analysis](docs/images/crash-detail.png) |

Slack notification:

![Slack alert](docs/images/slack-alert.png)
-->

To capture: run the end-to-end demo below, open the dashboard at `http://localhost:3000`,
and save PNGs as `docs/images/dashboard.png`, `docs/images/crash-detail.png`, and
`docs/images/slack-alert.png`. Then uncomment the block above.

---

## Architecture

```
Docker host ──(TCP)──▶ DockerMonitor ──▶ Redis stream ──▶ Worker ──▶ LangGraph workflow
                         (thread + asyncio bridge)                    │
                                                                      ▼
                                            analyze_crash ◀── FixAgent ◀── Qdrant cache (fastembed)
                                                  │                  │
                                       restart_likely_fixes?          │ cache miss → OpenAI LLM
                                           yes  │  no                 │ cache hit  → reuse analysis
                                                ▼  ▼
                                           attempt_restart     notify_slack ──▶ send_email ──▶ log_event
                                                  │                                               │
                                           success? True: log_event                               ▼
                                           success? False: notify_slack ───────────────▶ persist row
```

**Four processes:**

- **API server** (`src.api.app`) — FastAPI, auth, CRUD, dashboard endpoints, WebSocket for live updates.
- **Worker** (`src.worker.main`) — Docker event listeners + LangGraph orchestrator.
- **Frontend** (`frontend/`) — Next.js 15 + Shadcn/ui dashboard (scaffolded).
- **Agent container** (`src.agent_container.main`) — customer-hosted agent (skeleton; not wired end-to-end yet).

**Infra services** (via Docker Compose): PostgreSQL 16, Redis 7, Qdrant, Prometheus, Grafana.

---

## Prerequisites

- **Python 3.12** (project uses `py -3.12` on Windows; install via https://www.python.org/).
- **Docker Desktop** (for running `postgres`, `redis`, `qdrant` via compose).
- **Node.js 18+** (only for the frontend; optional if you just run backend).
- **OpenAI API key** — from https://platform.openai.com/api-keys.
- **Gmail account with 2FA + app password** — for email delivery. Create an app password at https://myaccount.google.com/apppasswords.
- **Slack incoming webhook URL** (optional, for Slack notifications) — Slack → Apps → Incoming Webhooks.

---

## Setup

### 1. Clone + install

```bash
git clone https://github.com/your-org/docker-sentinel.git
cd docker-sentinel

# Python deps
py -3.12 -m pip install -e ".[dev]"
# First run will also pull fastembed + OpenAI SDK + aiosmtplib

# Frontend deps (optional)
cd frontend && npm install && cd ..
```

### 2. Configure `.env`

Copy the example and fill in the real values:

```bash
cp .env.example .env
```

Required for the end-to-end notification demo:

```dotenv
# Database (defaults work with docker compose)
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel
DATABASE_URL_SYNC=postgresql://sentinel:sentinel@localhost:5432/sentinel

# Redis (defaults work)
REDIS_URL=redis://localhost:6379/0

# Qdrant (defaults work)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# LLM — OpenAI (primary + fallback)
OPENAI_API_KEY=sk-proj-...

# Email — Gmail SMTP (app password, not your Google account password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourname@gmail.com
SMTP_PASSWORD=<16-char app password from myaccount.google.com/apppasswords>
SMTP_FROM_EMAIL=yourname@gmail.com

# Slack — incoming webhook for the smoke test
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
```

The following values in `.env.example` are **not required** for Phase 2 demo and can stay as placeholders: GitHub/Google OAuth, JWT secret (works with default), LangSmith, SendGrid, Twilio.

### 3. Start infrastructure

```bash
docker compose up -d postgres redis qdrant
```

Wait ~5 s, then verify:

```bash
docker compose ps
```

All three should be `healthy`.

### 4. Run database migrations

```bash
py -3.12 -m alembic upgrade head
```

Expected output ends with: `Running upgrade ... Initial schema with all tables`.

---

## Running the end-to-end demo

### 1. Seed a tenant + Docker host

```bash
PYTHONPATH=. py -3.12 scripts/smoke_seed.py
```

Prints `TENANT_ID=<uuid>` and `HOST_ID=<uuid>`. Copy the `TENANT_ID`.

### 2. Seed notification configs from `.env`

```bash
SMOKE_TENANT_ID=<paste-from-step-1> PYTHONPATH=. py -3.12 scripts/smoke_seed_notifications.py
```

Inserts two `NotificationConfig` rows (Slack + email) pointing at your `.env` values.

### 3. Start the worker

```bash
PYTHONPATH=. py -3.12 -u -m src.worker.main
```

Leave this running in its own terminal. First-run caveat: the fastembed model (~80 MB) downloads on the first cache lookup — allow ~30 s on a fresh machine.

Logs should show:
```
Starting DockerSentinel worker
Spawning listener for host <id>
Started DockerMonitor for host <id>
```

### 4. Trigger a crash

In another terminal:

```bash
docker run --name port-conflict-demo busybox sh -c 'echo "ERROR: port 8080 already in use" >&2; exit 1'
```

Wait ~10 s for: LLM analysis → Slack POST → SMTP send → DB update.

### 5. Verify the results

**Slack** — a Block Kit message should appear in your configured channel with container name, image, exit code, severity, root cause, and up to 3 suggested fixes.

**Gmail** — an HTML email arrives with subject `[DockerSentinel] Crash: port-conflict-demo`.

**Database:**

```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "SELECT container_name, cache_hit, LEFT(root_cause, 60) AS root_cause, severity, slack_sent, email_sent, resolved_at IS NOT NULL AS resolved FROM crash_events WHERE container_name='port-conflict-demo';"
```

Expected: one row, `cache_hit=f` (first occurrence), `slack_sent=t`, `email_sent=t`, `resolved=t`.

**Qdrant cache:**

```bash
curl -s http://localhost:6333/collections/crash_history | grep -o '"points_count":[0-9]*'
```

Should show `"points_count":1` or more (other host crashes may also have been captured).

### 6. Optional — verify the cache hit

Run the same crash again with a different container name:

```bash
docker run --name port-conflict-demo-2 busybox sh -c 'echo "ERROR: port 8080 already in use" >&2; exit 1'
```

After ~5 s, the new row should have `cache_hit=t` — no OpenAI HTTP request in the worker log.

### 7. Tear down

```bash
docker rm -f port-conflict-demo port-conflict-demo-2
# Stop the worker with Ctrl+C (or on Windows: taskkill //F //IM python.exe)
docker compose down
```

---

## Running the API server + frontend

Optional for the current scope; the dashboard is not yet wired to live workflow data, but the scaffolding is in place.

```bash
# Terminal 1: API
uvicorn src.api.app:create_app --factory --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Open http://localhost:3000
```

---

## Testing

```bash
# Run all unit + schema tests (no real API calls, no live infra)
py -3.12 -m pytest tests/unit/ tests/test_services/test_crash_event_schema.py -v
```

Expected: **163 passed**.

```bash
# Optional: integration tests against a live stack (docker compose up -d redis)
PYTHONPATH=. py -3.12 -m pytest tests/integration -v -m integration
```

### Structure

- `tests/unit/listener/` — Docker event listener, manager, dedup, filter, bridge backpressure
- `tests/unit/worker/` — tenant supervisor, `_process_event`, consumer ack/reclaim
- `tests/unit/orchestrator/` — nodes, conditional edges, compiled-workflow E2E
- `tests/unit/agents/` — FixAgent, SlackAgent, EmailAgent, prompt builder
- `tests/unit/services/` — CrashMemory (Qdrant), NotificationConfig, DockerHost probe
- `tests/integration/` — real Redis stream round-trip (consume/ack/reclaim); skipped if unreachable

Unit tests never call OpenAI, Slack, SMTP, Qdrant, or Docker — all external integrations are mocked.

---

## Design & planning docs

All brainstorming specs + implementation plans live under `docs/superpowers/`:

### Specs

- `2026-04-12-dockersentinel-saas-skeleton-design.md` — original architecture
- `2026-04-21-crash-ingestion-pipeline-design.md` — Phase 1 listener + manager + worker
- `2026-04-21-orchestrator-nodes-design.md` — Phase 1 graph nodes
- `2026-04-22-fix-agent-design.md` — Phase 2 OpenAI-backed Fix Agent
- `2026-04-22-qdrant-memory-design.md` — Phase 3 vector cache
- `2026-04-23-notification-agents-design.md` — Phase 2 Slack + Email agents

### Plans

One implementation plan per spec, in `docs/superpowers/plans/`. Each lists bite-sized TDD tasks, used by the subagent-driven development workflow.

### Progress tracker

`work-tracking/PROGRESS.md` — running log of completed work, known deferred items, and next-session pickup notes.

---

## Project conventions

From `CLAUDE.md`:

- **Architecture:** FastAPI API server + separate Worker Process (same codebase, two Docker Compose services).
- **Multi-tenant:** every DB table has `tenant_id`, filtered at the service layer.
- **Async everywhere:** SQLAlchemy async sessions, FastAPI async endpoints, asyncio worker.
- **Service layer:** routers → services → models; routers never touch the DB directly.
- **Conventions:** Python 3.11+, type hints on all signatures, Ruff lint (line length 100), pytest + pytest-asyncio, conventional commits.

---

## Stack

Python 3.12 · FastAPI · LangGraph · Next.js 15 · Shadcn/ui · Tailwind · SQLAlchemy (async) · PostgreSQL 16 · Redis 7 · Qdrant · fastembed (bge-small-en-v1.5) · OpenAI · Jinja2 · aiosmtplib · httpx · Prometheus · Grafana

---

## Author

**Ashif Husain**

- GitHub: [@ashifhusainoo7](https://github.com/ashifhusainoo7)
- LinkedIn: [ashifhoo7](https://linkedin.com/in/ashifhoo7)
- Email: [mdashifhusain@gmail.com](mailto:mdashifhusain@gmail.com)

## License

[MIT](LICENSE)
