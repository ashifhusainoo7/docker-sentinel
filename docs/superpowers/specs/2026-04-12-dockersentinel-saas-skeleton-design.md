# DockerSentinel SaaS — Production Skeleton Design

## Context

DockerSentinel is a multi-agent AI system that monitors Docker containers in real-time, diagnoses crashes, attempts recovery, and escalates via Slack/email/phone. The original design targets a single Docker host. This spec extends it into a **multi-tenant SaaS platform** where tenants onboard via a web UI, connect their Docker hosts (via Direct TCP or a lightweight agent), and get per-tenant crash monitoring, dashboards, and notifications.

**Goal of this skeleton:** Build the complete production-grade project structure with all files, configs, schemas, routes, pages, and placeholder agent functions — so that the user can fill in agent/LLM logic step by step.

## Architecture: Hybrid API Server + Worker

Two processes from the same codebase, deployed as separate Docker Compose services:

### API Server (FastAPI)
- OAuth authentication (GitHub + Google) with JWT access/refresh tokens
- Tenant management CRUD
- Docker host registration (Direct TCP or Agent mode)
- Container filter/whitelist configuration
- Notification channel configuration (platform defaults + tenant overrides)
- API key management (for agent auth + programmatic access)
- WebSocket endpoint for agent connections
- Dashboard data API (crash events, analytics, summaries)
- Prometheus metrics endpoint (`/metrics`)

### Worker Process
- Polls PostgreSQL for active tenant Docker host configurations
- Spawns async Docker listeners per-tenant per-host (Direct TCP mode)
- Receives agent crash events via Redis pub/sub (API Server accepts WebSocket from agents, publishes events to Redis channel `agent:events:{tenant_id}`, Worker subscribes)
- Pushes CrashEvents to Redis Streams (keyed by tenant)
- Consumes Redis Streams, runs LangGraph orchestrator per event
- Dispatches to 5 agents: Fix, Slack, Email, Call, Dashboard
- Stores results in PostgreSQL + Qdrant

### Agent Container (dockersentinel/agent)
- Lightweight Docker container tenants run on their hosts
- Mounts local `/var/run/docker.sock`
- Authenticates to platform via API key
- Streams Docker events back via WebSocket (outbound connection)
- No firewall/port exposure needed on tenant side

## Dual Connectivity Modes

| Mode | Setup | Connection | Best For |
|------|-------|-----------|----------|
| Direct TCP | Tenant enters `tcp://host:port` in UI | Worker → Docker daemon | Internal networks, dev |
| Agent | Tenant runs `docker run dockersentinel/agent --token KEY` | Agent → Platform WebSocket | Cloud VMs, firewalled hosts |

Both modes produce the same `CrashEvent` schema → same Redis Stream → same LangGraph pipeline. The connectivity mode is invisible to the agent pipeline.

## Database Schema (PostgreSQL)

### tenants
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);
```

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    oauth_provider VARCHAR(50),  -- 'github' | 'google'
    oauth_provider_id VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',  -- 'owner' | 'admin' | 'member'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### api_keys
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    created_by UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,  -- bcrypt hash of the key
    key_prefix VARCHAR(12) NOT NULL, -- first 8 chars for identification
    scopes TEXT[] DEFAULT '{"agent"}',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### docker_hosts
```sql
CREATE TABLE docker_hosts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    connection_mode VARCHAR(20) NOT NULL, -- 'tcp' | 'agent'
    tcp_url TEXT,              -- for TCP mode: tcp://host:port
    tls_enabled BOOLEAN DEFAULT FALSE,
    tls_ca TEXT,               -- PEM cert for TLS
    tls_cert TEXT,
    tls_key TEXT,
    agent_id VARCHAR(255),     -- for agent mode: unique agent identifier
    agent_last_seen TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    monitor_all_containers BOOLEAN DEFAULT TRUE,
    container_filter JSONB DEFAULT '[]', -- whitelist: [{"name": "pattern"}, {"image": "pattern"}]
    status VARCHAR(50) DEFAULT 'pending', -- 'pending' | 'connected' | 'disconnected' | 'error'
    status_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### crash_events
```sql
CREATE TABLE crash_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    docker_host_id UUID NOT NULL REFERENCES docker_hosts(id),
    container_name VARCHAR(255) NOT NULL,
    container_id VARCHAR(64) NOT NULL,
    image TEXT NOT NULL,
    exit_code INTEGER,
    logs TEXT,
    timestamp TIMESTAMPTZ DEFAULT now(),
    root_cause TEXT,
    category VARCHAR(50),      -- 'oom' | 'dependency_failure' | 'config_error' | 'code_bug' | 'network' | 'unknown'
    severity VARCHAR(20),      -- 'critical' | 'high' | 'medium' | 'low'
    confidence REAL,
    restart_attempted BOOLEAN DEFAULT FALSE,
    restart_success BOOLEAN,
    cache_hit BOOLEAN DEFAULT FALSE,
    slack_sent BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    call_made BOOLEAN DEFAULT FALSE,
    suggestions JSONB DEFAULT '[]',
    llm_provider VARCHAR(50),
    llm_latency_ms INTEGER,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### notification_configs
```sql
CREATE TABLE notification_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    channel VARCHAR(50) NOT NULL, -- 'slack' | 'email' | 'call'
    is_enabled BOOLEAN DEFAULT TRUE,
    use_platform_default BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    -- slack: {"webhook_url": "..."}
    -- email: {"smtp_host": "...", "smtp_port": 587, "from_email": "...", "api_key": "..."}
    -- call: {"twilio_sid": "...", "twilio_token": "...", "from_number": "...", "on_call_phone": "..."}
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, channel)
);
```

### escalation_rules
```sql
CREATE TABLE escalation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    condition JSONB NOT NULL,  -- {"type": "multi_crash", "threshold": 2, "window_minutes": 5}
    action VARCHAR(50) NOT NULL, -- 'slack' | 'email' | 'call'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## API Routes (FastAPI)

### Auth
- `GET /api/v1/auth/github` — Initiate GitHub OAuth
- `GET /api/v1/auth/github/callback` — GitHub OAuth callback
- `GET /api/v1/auth/google` — Initiate Google OAuth
- `GET /api/v1/auth/google/callback` — Google OAuth callback
- `POST /api/v1/auth/refresh` — Refresh JWT token
- `POST /api/v1/auth/logout` — Invalidate session
- `GET /api/v1/auth/me` — Get current user + tenant

### Tenants
- `GET /api/v1/tenants/current` — Get current tenant details
- `PATCH /api/v1/tenants/current` — Update tenant settings
- `GET /api/v1/tenants/current/members` — List tenant members
- `POST /api/v1/tenants/current/members/invite` — Invite member

### Docker Hosts
- `GET /api/v1/hosts` — List Docker hosts for tenant
- `POST /api/v1/hosts` — Register a new Docker host
- `GET /api/v1/hosts/{id}` — Get host details + status
- `PATCH /api/v1/hosts/{id}` — Update host config
- `DELETE /api/v1/hosts/{id}` — Remove host
- `POST /api/v1/hosts/{id}/test` — Test connection to host
- `GET /api/v1/hosts/{id}/containers` — List containers on host

### API Keys
- `GET /api/v1/api-keys` — List API keys for tenant
- `POST /api/v1/api-keys` — Generate new API key
- `DELETE /api/v1/api-keys/{id}` — Revoke API key

### Crash Events
- `GET /api/v1/crashes` — List crash events (paginated, filterable)
- `GET /api/v1/crashes/{id}` — Get crash event details
- `GET /api/v1/crashes/stats` — Crash analytics (counts, categories, timelines)
- `GET /api/v1/crashes/top-crashers` — Top crashing containers

### Notifications
- `GET /api/v1/notifications/config` — Get notification configs for tenant
- `PUT /api/v1/notifications/config/{channel}` — Update notification config
- `POST /api/v1/notifications/test/{channel}` — Send test notification

### Escalation Rules
- `GET /api/v1/escalations` — List escalation rules
- `POST /api/v1/escalations` — Create escalation rule
- `PATCH /api/v1/escalations/{id}` — Update rule
- `DELETE /api/v1/escalations/{id}` — Delete rule

### Dashboard
- `GET /api/v1/dashboard/summary` — AI-generated summary
- `GET /api/v1/dashboard/metrics` — Key metrics (MTTR, cache hit rate, etc.)
- `GET /api/v1/dashboard/timeline` — Crash timeline data

### WebSocket
- `WS /api/v1/ws/agent` — Agent connection endpoint (authenticated via API key)
- `WS /api/v1/ws/live` — Live crash feed for dashboard

### Health
- `GET /health` — API health check
- `GET /metrics` — Prometheus metrics

## Frontend Pages (Next.js App Router)

```
app/
├── (auth)/
│   ├── login/page.tsx          — OAuth login (GitHub + Google buttons)
│   └── callback/page.tsx       — OAuth callback handler
├── (dashboard)/
│   ├── layout.tsx              — Authenticated layout with sidebar
│   ├── page.tsx                — Dashboard home (crash summary, charts, AI summary)
│   ├── crashes/
│   │   ├── page.tsx            — Crash events list (table with filters)
│   │   └── [id]/page.tsx       — Crash event detail (logs, analysis, actions taken)
│   ├── hosts/
│   │   ├── page.tsx            — Docker hosts list with status indicators
│   │   └── new/page.tsx        — Add Docker host (TCP or Agent mode)
│   ├── settings/
│   │   ├── page.tsx            — General tenant settings
│   │   ├── notifications/page.tsx — Notification channel config
│   │   ├── api-keys/page.tsx   — API key management
│   │   ├── escalations/page.tsx — Escalation rules
│   │   └── members/page.tsx    — Team member management
│   └── onboarding/page.tsx     — First-time setup wizard (name → add host → configure notifications)
└── api/                        — Next.js API routes (proxy to FastAPI if needed)
```

## Project Structure

```
docker-sentinel/
├── docker-compose.yml              # Full stack: api, worker, agent, postgres, redis, qdrant, prometheus, grafana
├── docker-compose.dev.yml          # Dev overrides (hot reload, debug ports)
├── Dockerfile                      # API + Worker (shared image, different entrypoints)
├── Dockerfile.agent                # Lightweight agent image
├── pyproject.toml                  # Python dependencies + project config
├── alembic.ini                     # Alembic migration config
├── .env.example                    # All environment variables documented
├── .gitignore
├── CLAUDE.md                       # Project conventions for Claude Code
├── README.md
│
├── config/
│   ├── settings.py                 # Pydantic Settings (env-based config)
│   ├── prometheus.yml              # Prometheus scrape config
│   └── grafana/
│       └── dashboards/
│           └── sentinel.json       # Pre-built Grafana dashboard
│
├── alembic/
│   ├── env.py
│   └── versions/                   # Migration files
│       └── 001_initial_schema.py
│
├── src/
│   ├── __init__.py
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                 # Base model with tenant_id mixin
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── docker_host.py
│   │   ├── crash_event.py
│   │   ├── api_key.py
│   │   ├── notification_config.py
│   │   └── escalation_rule.py
│   │
│   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── tenant.py
│   │   ├── docker_host.py
│   │   ├── crash_event.py          # Includes CrashAnalysis from design doc
│   │   ├── api_key.py
│   │   ├── notification.py
│   │   ├── escalation.py
│   │   └── dashboard.py
│   │
│   ├── api/                        # FastAPI application
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI app factory
│   │   ├── deps.py                 # Shared dependencies (get_db, get_current_user, get_tenant)
│   │   ├── middleware.py           # CORS, tenant context, request logging
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── tenants.py
│   │       ├── docker_hosts.py
│   │       ├── crash_events.py
│   │       ├── api_keys.py
│   │       ├── notifications.py
│   │       ├── escalations.py
│   │       ├── dashboard.py
│   │       ├── websocket.py        # Agent WS + live feed WS
│   │       └── health.py
│   │
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py         # OAuth + JWT logic
│   │   ├── tenant_service.py
│   │   ├── docker_host_service.py
│   │   ├── crash_event_service.py
│   │   ├── notification_service.py
│   │   ├── api_key_service.py
│   │   ├── redis_stream.py         # Redis Stream pub/sub
│   │   ├── database.py             # Async SQLAlchemy session management
│   │   ├── crash_memory.py         # Qdrant vector cache (placeholder)
│   │   └── metrics.py              # Prometheus counters/histograms
│   │
│   ├── agents/                     # LLM agents (placeholder logic)
│   │   ├── __init__.py
│   │   ├── fix_agent.py            # Root cause analysis (Haiku + Qdrant cache)
│   │   ├── slack_agent.py          # Slack notifications
│   │   ├── email_agent.py          # Email reports
│   │   ├── call_agent.py           # Twilio voice calls
│   │   └── dashboard_agent.py      # AI summary generator
│   │
│   ├── orchestrator/               # LangGraph state machine
│   │   ├── __init__.py
│   │   ├── state.py                # CrashState TypedDict
│   │   ├── graph.py                # StateGraph definition with nodes + edges
│   │   └── nodes.py                # Node functions (analyze, restart, notify, log)
│   │
│   ├── listener/                   # Docker event listeners
│   │   ├── __init__.py
│   │   ├── docker_monitor.py       # Direct TCP Docker SDK listener (placeholder)
│   │   └── manager.py              # Listener lifecycle manager (spawn/stop per host)
│   │
│   ├── worker/                     # Worker process entrypoint
│   │   ├── __init__.py
│   │   └── main.py                 # Worker main loop: manage listeners + consume Redis
│   │
│   ├── agent_container/            # Agent container source
│   │   ├── __init__.py
│   │   ├── main.py                 # Agent entrypoint: docker.sock → WebSocket
│   │   └── requirements.txt        # Minimal deps for agent image
│   │
│   └── templates/
│       └── crash_email.html        # Jinja2 email template
│
├── frontend/                       # Next.js application
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── components.json             # Shadcn/ui config
│   ├── .env.local.example
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Landing / redirect to dashboard
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── callback/page.tsx
│   │   │   └── (dashboard)/
│   │   │       ├── layout.tsx      # Sidebar + header layout
│   │   │       ├── page.tsx        # Dashboard home
│   │   │       ├── crashes/
│   │   │       │   ├── page.tsx
│   │   │       │   └── [id]/page.tsx
│   │   │       ├── hosts/
│   │   │       │   ├── page.tsx
│   │   │       │   └── new/page.tsx
│   │   │       ├── settings/
│   │   │       │   ├── page.tsx
│   │   │       │   ├── notifications/page.tsx
│   │   │       │   ├── api-keys/page.tsx
│   │   │       │   ├── escalations/page.tsx
│   │   │       │   └── members/page.tsx
│   │   │       └── onboarding/page.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                 # Shadcn/ui components (installed via CLI)
│   │   │   ├── layout/
│   │   │   │   ├── sidebar.tsx
│   │   │   │   ├── header.tsx
│   │   │   │   └── nav-links.tsx
│   │   │   ├── crashes/
│   │   │   │   ├── crash-table.tsx
│   │   │   │   ├── crash-detail.tsx
│   │   │   │   └── crash-charts.tsx
│   │   │   ├── hosts/
│   │   │   │   ├── host-card.tsx
│   │   │   │   └── add-host-form.tsx
│   │   │   └── dashboard/
│   │   │       ├── stats-cards.tsx
│   │   │       ├── crash-timeline.tsx
│   │   │       └── ai-summary.tsx
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts              # API client (fetch wrapper with auth)
│   │   │   ├── auth.ts             # Auth helpers (token storage, refresh)
│   │   │   └── utils.ts            # Shared utilities
│   │   │
│   │   └── hooks/
│   │       ├── use-auth.ts         # Auth context hook
│   │       ├── use-crashes.ts      # Crash data fetching
│   │       └── use-websocket.ts    # Live crash feed
│   │
│   └── public/
│       └── logo.svg
│
├── tests/
│   ├── conftest.py                 # Pytest fixtures (test DB, test client, auth helpers)
│   ├── test_api/
│   │   ├── test_auth.py
│   │   ├── test_hosts.py
│   │   └── test_crashes.py
│   └── test_services/
│       ├── test_crash_event.py
│       └── test_orchestrator.py
│
├── scripts/
│   ├── simulate_crash.py           # Crash simulator for demos
│   ├── seed_db.py                  # Test data seeder
│   └── generate_api_key.py         # CLI tool to generate API keys
│
└── .github/
    └── workflows/
        └── ci.yml                  # pytest + ruff + Docker build
```

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| API Framework | FastAPI (async) |
| Frontend | Next.js 15 + React 19 + Shadcn/ui + Tailwind |
| Agent Framework | LangGraph + LangChain |
| Primary LLM | Claude Haiku 4.5 (placeholder in skeleton) |
| Fallback LLM | OpenAI gpt-4o-mini (placeholder in skeleton) |
| Database | PostgreSQL 16 (via Docker Compose) |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Cache/Queue | Redis 7 (Streams for events, pub/sub for agent WS) |
| Vector DB | Qdrant (local Docker mode) |
| Auth | OAuth2 (GitHub + Google) + JWT (access + refresh tokens) |
| Observability | LangSmith + Prometheus + Grafana |
| Containerization | Docker Compose (api, worker, agent, postgres, redis, qdrant, prometheus, grafana) |
| CI/CD | GitHub Actions |

## What the Skeleton Includes vs. Excludes

### Includes (fully implemented)
- All file/folder structure
- Docker Compose with all services wired together
- Dockerfiles (API/Worker + Agent)
- PostgreSQL schema via Alembic migrations
- SQLAlchemy models with tenant isolation mixin
- Pydantic schemas for all data types
- FastAPI routers with all endpoints (request/response wired, business logic calls service layer)
- Service layer with method signatures and docstrings
- Auth flow (OAuth + JWT) fully wired
- Middleware (CORS, tenant context)
- FastAPI dependencies (get_db, get_current_user, get_tenant)
- LangGraph state machine structure (nodes defined, edges wired)
- Agent class skeletons with `analyze()`, `notify()`, `send()`, `escalate()` methods
- Prometheus metrics definitions
- Next.js app with all pages, layouts, and component shells
- Shadcn/ui installed with core components
- API client library for frontend
- WebSocket endpoint structure
- `.env.example` with all variables documented
- CI workflow (pytest + ruff + Docker build)
- CLAUDE.md with project conventions

### Excludes (user fills in step by step)
- Actual LLM call logic in agents
- Qdrant vector search/store implementation
- Prompt engineering / few-shot examples
- Docker event listener logic (connecting to daemons, parsing events)
- Agent container event streaming logic
- Notification sending logic (Slack webhook, SMTP, Twilio)
- LangGraph node function bodies (currently raise NotImplementedError)
- Frontend data fetching / state management wiring
- Grafana dashboard JSON (panel definitions)

## Verification Plan

1. `docker compose up` starts all services without errors
2. `alembic upgrade head` creates all tables in PostgreSQL
3. FastAPI serves on `:8000` with Swagger docs at `/docs`
4. Next.js serves on `:3000` with login page
5. Prometheus scrapes metrics from `:9090`
6. `pytest` discovers and runs test files (tests may be placeholder/skip)
7. `ruff check src/` passes with no linting errors
8. Agent placeholder methods raise `NotImplementedError` with descriptive messages
