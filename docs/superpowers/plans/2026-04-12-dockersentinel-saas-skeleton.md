# DockerSentinel SaaS Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete production-grade skeleton for DockerSentinel — a multi-tenant SaaS Docker crash monitoring platform — with all files, configs, schemas, routes, pages, and placeholder agent functions ready for the user to fill in logic step by step.

**Architecture:** Hybrid two-process design: FastAPI API Server (auth, CRUD, WebSocket) + Worker Process (Docker listeners, Redis consumer, LangGraph orchestrator). Dual connectivity: Direct TCP to Docker daemons or lightweight agent container that phones home via WebSocket. Multi-tenant PostgreSQL with `tenant_id` isolation.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, LangGraph, Redis Streams, Qdrant, PostgreSQL 16, Next.js 15, React 19, Shadcn/ui, Tailwind CSS, Docker Compose, Prometheus, Grafana, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-04-12-dockersentinel-saas-skeleton-design.md`

---

## File Structure Overview

### Root config files
- `pyproject.toml` — Python project config + dependencies
- `alembic.ini` — Alembic migration config
- `.env.example` — All env vars documented
- `.gitignore` — Python, Node, Docker ignores
- `CLAUDE.md` — Project conventions
- `docker-compose.yml` — Full stack services
- `docker-compose.dev.yml` — Dev overrides
- `Dockerfile` — API + Worker image
- `Dockerfile.agent` — Lightweight agent image

### Config
- `config/settings.py` — Pydantic Settings class
- `config/prometheus.yml` — Prometheus scrape config

### Database
- `alembic/env.py` — Alembic env with async engine
- `alembic/versions/001_initial_schema.py` — All tables

### Models (SQLAlchemy)
- `src/models/base.py` — Base + TenantMixin
- `src/models/tenant.py` — Tenant model
- `src/models/user.py` — User model
- `src/models/docker_host.py` — DockerHost model
- `src/models/crash_event.py` — CrashEvent model
- `src/models/api_key.py` — ApiKey model
- `src/models/notification_config.py` — NotificationConfig model
- `src/models/escalation_rule.py` — EscalationRule model
- `src/models/__init__.py` — Re-exports all models

### Schemas (Pydantic)
- `src/schemas/auth.py` — Token, UserResponse, OAuthCallback
- `src/schemas/tenant.py` — TenantCreate, TenantResponse, TenantUpdate
- `src/schemas/docker_host.py` — HostCreate, HostResponse, HostUpdate
- `src/schemas/crash_event.py` — CrashEvent, CrashAnalysis, CrashResponse
- `src/schemas/api_key.py` — ApiKeyCreate, ApiKeyResponse
- `src/schemas/notification.py` — NotificationConfigUpdate, NotificationConfigResponse
- `src/schemas/escalation.py` — EscalationCreate, EscalationResponse
- `src/schemas/dashboard.py` — DashboardSummary, MetricsResponse, TimelineResponse

### Services
- `src/services/database.py` — Async session factory
- `src/services/auth_service.py` — OAuth + JWT
- `src/services/tenant_service.py` — Tenant CRUD
- `src/services/docker_host_service.py` — Host CRUD
- `src/services/crash_event_service.py` — Crash CRUD + analytics
- `src/services/api_key_service.py` — API key management
- `src/services/notification_service.py` — Notification config CRUD
- `src/services/redis_stream.py` — Redis Stream pub/sub
- `src/services/crash_memory.py` — Qdrant placeholder
- `src/services/metrics.py` — Prometheus metrics

### API
- `src/api/app.py` — FastAPI app factory
- `src/api/deps.py` — Dependencies (get_db, get_current_user, get_tenant)
- `src/api/middleware.py` — CORS, request logging
- `src/api/routers/auth.py` — Auth routes
- `src/api/routers/tenants.py` — Tenant routes
- `src/api/routers/docker_hosts.py` — Host routes
- `src/api/routers/crash_events.py` — Crash routes
- `src/api/routers/api_keys.py` — API key routes
- `src/api/routers/notifications.py` — Notification routes
- `src/api/routers/escalations.py` — Escalation routes
- `src/api/routers/dashboard.py` — Dashboard routes
- `src/api/routers/websocket.py` — WebSocket endpoints
- `src/api/routers/health.py` — Health + metrics
- `src/api/routers/__init__.py` — Router registration

### Orchestrator
- `src/orchestrator/state.py` — CrashState TypedDict
- `src/orchestrator/nodes.py` — Node functions (placeholders)
- `src/orchestrator/graph.py` — StateGraph with edges

### Agents
- `src/agents/fix_agent.py` — FixAgent placeholder
- `src/agents/slack_agent.py` — SlackAgent placeholder
- `src/agents/email_agent.py` — EmailAgent placeholder
- `src/agents/call_agent.py` — CallAgent placeholder
- `src/agents/dashboard_agent.py` — DashboardAgent placeholder
- `src/agents/__init__.py` — Re-exports

### Listener + Worker
- `src/listener/docker_monitor.py` — DockerMonitor placeholder
- `src/listener/manager.py` — ListenerManager placeholder
- `src/worker/main.py` — Worker entrypoint

### Agent Container
- `src/agent_container/main.py` — Agent entrypoint placeholder
- `src/agent_container/requirements.txt` — Minimal deps

### Templates
- `src/templates/crash_email.html` — Jinja2 email template

### Tests
- `tests/conftest.py` — Fixtures
- `tests/test_api/test_auth.py`
- `tests/test_api/test_hosts.py`
- `tests/test_api/test_crashes.py`
- `tests/test_services/test_crash_event.py`
- `tests/test_services/test_orchestrator.py`

### Scripts
- `scripts/simulate_crash.py`
- `scripts/seed_db.py`
- `scripts/generate_api_key.py`

### CI
- `.github/workflows/ci.yml`

### Frontend (Next.js) — Task 10+
- All files under `frontend/`

---

## Phase 1: Project Foundation

### Task 1: Initialize Git + Root Config Files

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `CLAUDE.md`

- [ ] **Step 1: Initialize git repo**

```bash
cd c:/docker-sentinel
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
env/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
data/

# Node / Frontend
frontend/node_modules/
frontend/.next/
frontend/out/

# Alembic
alembic/versions/__pycache__/

# OS
.DS_Store
Thumbs.db

# Superpowers
.superpowers/

# Qdrant local data
qdrant_data/
```

- [ ] **Step 3: Create pyproject.toml**

```toml
[project]
name = "docker-sentinel"
version = "0.1.0"
description = "Multi-Agent Docker Container Crash Monitor — SaaS Platform"
requires-python = ">=3.11"
dependencies = [
    # API
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-multipart>=0.0.9",
    # Database
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    # Redis
    "redis[hiredis]>=5.0.0",
    # Auth
    "authlib>=1.3.0",
    "httpx>=0.27.0",
    "pyjwt[crypto]>=2.8.0",
    "bcrypt>=4.1.0",
    # LLM / Agents
    "langgraph>=1.0.0",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "langchain-openai>=0.3.0",
    # Vector DB
    "qdrant-client>=1.9.0",
    "langchain-qdrant>=0.2.0",
    # Docker
    "docker>=7.0.0",
    # Observability
    "prometheus-client>=0.20.0",
    "langsmith>=0.1.0",
    # Notifications
    "jinja2>=3.1.0",
    "twilio>=9.0.0",
    # Config
    "pydantic-settings>=2.2.0",
    "pyyaml>=6.0.0",
    # WebSocket
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
    "aiosqlite>=0.20.0",
]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Create .env.example**

```bash
# === Database ===
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel
DATABASE_URL_SYNC=postgresql://sentinel:sentinel@localhost:5432/sentinel

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === Auth — GitHub OAuth ===
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# === Auth — Google OAuth ===
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# === JWT ===
JWT_SECRET_KEY=change-this-to-a-random-64-char-string
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# === LLM — Anthropic (Primary) ===
ANTHROPIC_API_KEY=your_anthropic_api_key

# === LLM — OpenAI (Fallback) ===
OPENAI_API_KEY=your_openai_api_key

# === LangSmith Tracing ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=docker-sentinel

# === Qdrant ===
QDRANT_HOST=localhost
QDRANT_PORT=6333

# === Notifications — Platform Defaults ===
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SENDGRID_API_KEY=your_sendgrid_api_key
SMTP_FROM_EMAIL=sentinel@yourdomain.com
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=+1234567890

# === App ===
APP_URL=http://localhost:3000
API_URL=http://localhost:8000
ENVIRONMENT=development
```

- [ ] **Step 5: Create CLAUDE.md**

```markdown
# DockerSentinel — Project Conventions

## Architecture
- **API Server** (FastAPI): `src/api/` — auth, CRUD, WebSocket, metrics
- **Worker Process**: `src/worker/` — Docker listeners, Redis consumer, LangGraph orchestrator
- **Agent Container**: `src/agent_container/` — lightweight image tenants deploy on their hosts
- **Frontend** (Next.js): `frontend/` — Shadcn/ui + Tailwind dashboard

## Key Patterns
- Multi-tenant: every DB table has `tenant_id`, enforced via `get_tenant` dependency
- Async everywhere: SQLAlchemy async sessions, FastAPI async endpoints, asyncio worker
- Service layer: routers call services, services call models — routers never touch DB directly
- Schemas: Pydantic models in `src/schemas/` for request/response validation
- Models: SQLAlchemy ORM in `src/models/` with `TenantMixin` base

## Commands
- **Run API**: `uvicorn src.api.app:create_app --factory --reload --port 8000`
- **Run Worker**: `python -m src.worker.main`
- **Run Frontend**: `cd frontend && npm run dev`
- **Run Tests**: `pytest`
- **Lint**: `ruff check src/ tests/`
- **Migrations**: `alembic upgrade head`
- **Full Stack**: `docker compose up`

## Agent Placeholders
All agent methods raise `NotImplementedError` with descriptive messages.
The user will fill in LLM logic, prompts, and notification sending step by step.

## Conventions
- Python 3.11+, type hints on all function signatures
- Ruff for linting (line length 100)
- pytest + pytest-asyncio for tests
- Commits: conventional commits (`feat:`, `fix:`, `chore:`)
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore pyproject.toml .env.example CLAUDE.md
git commit -m "chore: initialize project with config files"
```

---

### Task 2: Docker Compose + Dockerfiles

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `Dockerfile`
- Create: `Dockerfile.agent`
- Create: `config/prometheus.yml`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m src.worker.main
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: sentinel
      POSTGRES_DB: sentinel
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=sentinel
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  prometheus_data:
  grafana_data:
```

- [ ] **Step 2: Create docker-compose.dev.yml**

```yaml
services:
  api:
    command: uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
      - /app/.venv
    environment:
      - ENVIRONMENT=development

  worker:
    volumes:
      - .:/app
      - /app/.venv
    environment:
      - ENVIRONMENT=development
```

- [ ] **Step 3: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY config/ config/
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create Dockerfile.agent**

```dockerfile
FROM python:3.11-slim

WORKDIR /agent

COPY src/agent_container/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/agent_container/ .

ENTRYPOINT ["python", "main.py"]
```

- [ ] **Step 5: Create config/prometheus.yml**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "sentinel-api"
    static_configs:
      - targets: ["api:8000"]
    metrics_path: "/metrics"

  - job_name: "sentinel-worker"
    static_configs:
      - targets: ["worker:9091"]
    metrics_path: "/metrics"
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml Dockerfile Dockerfile.agent config/prometheus.yml
git commit -m "chore: add Docker Compose, Dockerfiles, and Prometheus config"
```

---

## Phase 2: Database Layer

### Task 3: Pydantic Settings + Database Service

**Files:**
- Create: `config/__init__.py`
- Create: `config/settings.py`
- Create: `src/__init__.py`
- Create: `src/services/__init__.py`
- Create: `src/services/database.py`

- [ ] **Step 1: Create config/settings.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel"
    database_url_sync: str = "postgresql://sentinel:sentinel@localhost:5432/sentinel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth — GitHub
    github_client_id: str = ""
    github_client_secret: str = ""

    # Auth — Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT
    jwt_secret_key: str = "change-this-to-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "docker-sentinel"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Notifications — Platform Defaults
    slack_webhook_url: str = ""
    sendgrid_api_key: str = ""
    smtp_from_email: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # App
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    environment: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 2: Create src/services/database.py**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 3: Create __init__.py files**

Create empty `config/__init__.py`, `src/__init__.py`, `src/services/__init__.py`.

- [ ] **Step 4: Commit**

```bash
git add config/ src/__init__.py src/services/__init__.py src/services/database.py
git commit -m "feat: add Pydantic settings and async database service"
```

---

### Task 4: SQLAlchemy Models

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/base.py`
- Create: `src/models/tenant.py`
- Create: `src/models/user.py`
- Create: `src/models/docker_host.py`
- Create: `src/models/crash_event.py`
- Create: `src/models/api_key.py`
- Create: `src/models/notification_config.py`
- Create: `src/models/escalation_rule.py`

- [ ] **Step 1: Create src/models/base.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Mixin that adds tenant_id to any model for multi-tenant isolation."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

- [ ] **Step 2: Create src/models/tenant.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users = relationship("User", back_populates="tenant", lazy="selectin")
    docker_hosts = relationship("DockerHost", back_populates="tenant", lazy="selectin")
```

- [ ] **Step 3: Create src/models/user.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    oauth_provider: Mapped[str | None] = mapped_column(String(50))
    oauth_provider_id: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
```

- [ ] **Step 4: Create src/models/docker_host.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TenantMixin, TimestampMixin


class DockerHost(TenantMixin, TimestampMixin, Base):
    __tablename__ = "docker_hosts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # 'tcp' | 'agent'

    # TCP mode fields
    tcp_url: Mapped[str | None] = mapped_column(Text)
    tls_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tls_ca: Mapped[str | None] = mapped_column(Text)
    tls_cert: Mapped[str | None] = mapped_column(Text)
    tls_key: Mapped[str | None] = mapped_column(Text)

    # Agent mode fields
    agent_id: Mapped[str | None] = mapped_column(String(255))
    agent_last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Monitoring config
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_all_containers: Mapped[bool] = mapped_column(Boolean, default=True)
    container_filter: Mapped[dict] = mapped_column(JSONB, default=list)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    status_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    tenant = relationship("Tenant", back_populates="docker_hosts")
    crash_events = relationship("CrashEvent", back_populates="docker_host", lazy="selectin")
```

- [ ] **Step 5: Create src/models/crash_event.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TenantMixin


class CrashEvent(TenantMixin, Base):
    __tablename__ = "crash_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    docker_host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("docker_hosts.id"), nullable=False, index=True
    )
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    container_id: Mapped[str] = mapped_column(String(64), nullable=False)
    image: Mapped[str] = mapped_column(Text, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    logs: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Analysis results (filled by Fix Agent)
    root_cause: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))
    severity: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    suggestions: Mapped[dict] = mapped_column(JSONB, default=list)

    # Action tracking
    restart_attempted: Mapped[bool] = mapped_column(Boolean, default=False)
    restart_success: Mapped[bool | None] = mapped_column(Boolean)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    slack_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    call_made: Mapped[bool] = mapped_column(Boolean, default=False)

    # LLM metadata
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    docker_host = relationship("DockerHost", back_populates="crash_events")
```

- [ ] **Step 6: Create src/models/api_key.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TenantMixin


class ApiKey(TenantMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=lambda: ["agent"])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 7: Create src/models/notification_config.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TenantMixin


class NotificationConfig(TenantMixin, Base):
    __tablename__ = "notification_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "channel"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    use_platform_default: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 8: Create src/models/escalation_rule.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TenantMixin


class EscalationRule(TenantMixin, Base):
    __tablename__ = "escalation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 9: Create src/models/__init__.py**

```python
from src.models.api_key import ApiKey
from src.models.base import Base
from src.models.crash_event import CrashEvent
from src.models.docker_host import DockerHost
from src.models.escalation_rule import EscalationRule
from src.models.notification_config import NotificationConfig
from src.models.tenant import Tenant
from src.models.user import User

__all__ = [
    "Base",
    "Tenant",
    "User",
    "DockerHost",
    "CrashEvent",
    "ApiKey",
    "NotificationConfig",
    "EscalationRule",
]
```

- [ ] **Step 10: Commit**

```bash
git add src/models/
git commit -m "feat: add SQLAlchemy models with tenant isolation"
```

---

### Task 5: Alembic Migrations

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/001_initial_schema.py`

- [ ] **Step 1: Create alembic.ini**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Create alembic/env.py**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import settings
from src.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Create alembic/script.py.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: Create alembic/versions/001_initial_schema.py**

```python
"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2026-04-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("oauth_provider", sa.String(50)),
        sa.Column("oauth_provider_id", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "docker_hosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connection_mode", sa.String(20), nullable=False),
        sa.Column("tcp_url", sa.Text()),
        sa.Column("tls_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("tls_ca", sa.Text()),
        sa.Column("tls_cert", sa.Text()),
        sa.Column("tls_key", sa.Text()),
        sa.Column("agent_id", sa.String(255)),
        sa.Column("agent_last_seen", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("monitor_all_containers", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("container_filter", postgresql.JSONB(), server_default="[]"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("status_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "crash_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("docker_host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("docker_hosts.id"), nullable=False, index=True),
        sa.Column("container_name", sa.String(255), nullable=False),
        sa.Column("container_id", sa.String(64), nullable=False),
        sa.Column("image", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("logs", sa.Text()),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("root_cause", sa.Text()),
        sa.Column("category", sa.String(50)),
        sa.Column("severity", sa.String(20)),
        sa.Column("confidence", sa.Float()),
        sa.Column("suggestions", postgresql.JSONB(), server_default="[]"),
        sa.Column("restart_attempted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("restart_success", sa.Boolean()),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("slack_sent", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("email_sent", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("call_made", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("llm_latency_ms", sa.Integer()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notification_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("use_platform_default", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "channel"),
    )

    op.create_table(
        "escalation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("escalation_rules")
    op.drop_table("notification_configs")
    op.drop_table("crash_events")
    op.drop_table("docker_hosts")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("tenants")
```

- [ ] **Step 5: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: add Alembic migrations with initial schema"
```

---

## Phase 3: Pydantic Schemas

### Task 6: All Pydantic Schemas

**Files:**
- Create: `src/schemas/__init__.py`
- Create: `src/schemas/auth.py`
- Create: `src/schemas/tenant.py`
- Create: `src/schemas/docker_host.py`
- Create: `src/schemas/crash_event.py`
- Create: `src/schemas/api_key.py`
- Create: `src/schemas/notification.py`
- Create: `src/schemas/escalation.py`
- Create: `src/schemas/dashboard.py`

- [ ] **Step 1: Create src/schemas/auth.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
    oauth_provider: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: UserResponse
    tenant_name: str
    tenant_slug: str
```

- [ ] **Step 2: Create src/schemas/tenant.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    slug: str


class TenantUpdate(BaseModel):
    name: str | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteMember(BaseModel):
    email: str
    role: str = "member"
```

- [ ] **Step 3: Create src/schemas/docker_host.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class DockerHostCreate(BaseModel):
    name: str
    connection_mode: str  # 'tcp' | 'agent'
    tcp_url: str | None = None
    tls_enabled: bool = False
    monitor_all_containers: bool = True
    container_filter: list[dict] = []


class DockerHostUpdate(BaseModel):
    name: str | None = None
    tcp_url: str | None = None
    tls_enabled: bool | None = None
    is_active: bool | None = None
    monitor_all_containers: bool | None = None
    container_filter: list[dict] | None = None


class DockerHostResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    connection_mode: str
    tcp_url: str | None
    tls_enabled: bool
    agent_id: str | None
    agent_last_seen: datetime | None
    is_active: bool
    monitor_all_containers: bool
    container_filter: list[dict]
    status: str
    status_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContainerInfo(BaseModel):
    container_id: str
    name: str
    image: str
    status: str
    created: datetime
```

- [ ] **Step 4: Create src/schemas/crash_event.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CrashAnalysis(BaseModel):
    """Structured output from the Fix Agent — matches design doc exactly."""

    restart_likely_fixes: bool = Field(
        description="True if restart will likely resolve the issue"
    )
    root_cause: str = Field(description="One-line root cause summary")
    severity: str = Field(description="critical/high/medium/low")
    category: str = Field(
        description="oom | dependency_failure | config_error | code_bug | network | unknown"
    )
    suggestions: list[str] = Field(
        description="Ordered fix suggestions, most impactful first"
    )
    confidence: float = Field(description="0.0 to 1.0")


class CrashEventCreate(BaseModel):
    """Used internally when creating a crash event from Docker listener."""

    docker_host_id: uuid.UUID
    container_name: str
    container_id: str
    image: str
    exit_code: int | None = None
    logs: str | None = None


class CrashEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    docker_host_id: uuid.UUID
    container_name: str
    container_id: str
    image: str
    exit_code: int | None
    logs: str | None
    timestamp: datetime
    root_cause: str | None
    category: str | None
    severity: str | None
    confidence: float | None
    suggestions: list
    restart_attempted: bool
    restart_success: bool | None
    cache_hit: bool
    slack_sent: bool
    email_sent: bool
    call_made: bool
    llm_provider: str | None
    llm_latency_ms: int | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrashStats(BaseModel):
    total_crashes: int
    crashes_today: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    cache_hit_rate: float
    avg_resolution_time_ms: float | None


class TopCrasher(BaseModel):
    container_name: str
    crash_count: int
    last_crash: datetime
```

- [ ] **Step 5: Create src/schemas/api_key.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["agent"]
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(BaseModel):
    """Returned only on creation — includes the full key (shown once)."""

    id: uuid.UUID
    name: str
    key: str  # Full API key — only shown once
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None
```

- [ ] **Step 6: Create src/schemas/notification.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    use_platform_default: bool | None = None
    config: dict | None = None


class NotificationConfigResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    channel: str
    is_enabled: bool
    use_platform_default: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestNotificationRequest(BaseModel):
    message: str = "Test notification from DockerSentinel"
```

- [ ] **Step 7: Create src/schemas/escalation.py**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class EscalationRuleCreate(BaseModel):
    name: str
    condition: dict  # e.g. {"type": "multi_crash", "threshold": 2, "window_minutes": 5}
    action: str  # 'slack' | 'email' | 'call'


class EscalationRuleUpdate(BaseModel):
    name: str | None = None
    condition: dict | None = None
    action: str | None = None
    is_active: bool | None = None


class EscalationRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    condition: dict
    action: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 8: Create src/schemas/dashboard.py**

```python
from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    ai_summary: str
    total_crashes_24h: int
    total_restarts_24h: int
    active_containers: int
    cache_hit_rate: float


class MetricsResponse(BaseModel):
    mttr_seconds: float | None
    cache_hit_rate: float
    restart_success_rate: float
    crashes_per_hour: float
    top_category: str | None


class TimelinePoint(BaseModel):
    timestamp: datetime
    crash_count: int


class TimelineResponse(BaseModel):
    points: list[TimelinePoint]
    period: str  # '24h' | '7d' | '30d'
```

- [ ] **Step 9: Create src/schemas/__init__.py**

```python
from src.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from src.schemas.auth import MeResponse, Token, TokenRefresh, UserResponse
from src.schemas.crash_event import (
    CrashAnalysis,
    CrashEventCreate,
    CrashEventResponse,
    CrashStats,
    TopCrasher,
)
from src.schemas.dashboard import DashboardSummary, MetricsResponse, TimelineResponse
from src.schemas.docker_host import (
    ContainerInfo,
    DockerHostCreate,
    DockerHostResponse,
    DockerHostUpdate,
)
from src.schemas.escalation import (
    EscalationRuleCreate,
    EscalationRuleResponse,
    EscalationRuleUpdate,
)
from src.schemas.notification import (
    NotificationConfigResponse,
    NotificationConfigUpdate,
    TestNotificationRequest,
)
from src.schemas.tenant import (
    InviteMember,
    MemberResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)

__all__ = [
    "ApiKeyCreate",
    "ApiKeyCreated",
    "ApiKeyResponse",
    "CrashAnalysis",
    "CrashEventCreate",
    "CrashEventResponse",
    "CrashStats",
    "ContainerInfo",
    "DashboardSummary",
    "DockerHostCreate",
    "DockerHostResponse",
    "DockerHostUpdate",
    "EscalationRuleCreate",
    "EscalationRuleResponse",
    "EscalationRuleUpdate",
    "InviteMember",
    "MeResponse",
    "MemberResponse",
    "MetricsResponse",
    "NotificationConfigResponse",
    "NotificationConfigUpdate",
    "TenantCreate",
    "TenantResponse",
    "TenantUpdate",
    "TestNotificationRequest",
    "TimelineResponse",
    "Token",
    "TokenRefresh",
    "TopCrasher",
    "UserResponse",
]
```

- [ ] **Step 10: Commit**

```bash
git add src/schemas/
git commit -m "feat: add Pydantic schemas for all API data types"
```

---

## Phase 4: Services Layer

### Task 7: Core Services

**Files:**
- Create: `src/services/auth_service.py`
- Create: `src/services/tenant_service.py`
- Create: `src/services/docker_host_service.py`
- Create: `src/services/crash_event_service.py`
- Create: `src/services/api_key_service.py`
- Create: `src/services/notification_service.py`
- Create: `src/services/redis_stream.py`
- Create: `src/services/crash_memory.py`
- Create: `src/services/metrics.py`

- [ ] **Step 1: Create src/services/auth_service.py**

```python
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.models.tenant import Tenant
from src.models.user import User


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


async def get_or_create_user_from_oauth(
    db: AsyncSession,
    email: str,
    name: str | None,
    avatar_url: str | None,
    provider: str,
    provider_id: str,
) -> User:
    """Find existing user by email or create new user + tenant on first login."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        return user

    # Create new tenant for first-time user
    slug = email.split("@")[0].lower().replace(".", "-")
    tenant = Tenant(name=f"{name or slug}'s Workspace", slug=f"{slug}-{uuid.uuid4().hex[:6]}")
    db.add(tenant)
    await db.flush()

    # Create user as owner
    user = User(
        tenant_id=tenant.id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=provider,
        oauth_provider_id=provider_id,
        role="owner",
    )
    db.add(user)
    await db.flush()
    return user
```

- [ ] **Step 2: Create src/services/tenant_service.py**

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tenant import Tenant
from src.models.user import User


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


async def update_tenant(db: AsyncSession, tenant_id: uuid.UUID, name: str) -> Tenant:
    tenant = await get_tenant(db, tenant_id)
    if tenant and name:
        tenant.name = name
        await db.flush()
    return tenant


async def list_members(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.is_active == True)
    )
    return list(result.scalars().all())
```

- [ ] **Step 3: Create src/services/docker_host_service.py**

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.docker_host import DockerHost
from src.schemas.docker_host import DockerHostCreate, DockerHostUpdate


async def create_host(
    db: AsyncSession, tenant_id: uuid.UUID, data: DockerHostCreate
) -> DockerHost:
    host = DockerHost(
        tenant_id=tenant_id,
        name=data.name,
        connection_mode=data.connection_mode,
        tcp_url=data.tcp_url,
        tls_enabled=data.tls_enabled,
        monitor_all_containers=data.monitor_all_containers,
        container_filter=data.container_filter,
    )
    if data.connection_mode == "agent":
        host.agent_id = uuid.uuid4().hex
    db.add(host)
    await db.flush()
    return host


async def list_hosts(db: AsyncSession, tenant_id: uuid.UUID) -> list[DockerHost]:
    result = await db.execute(
        select(DockerHost).where(DockerHost.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def get_host(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID
) -> DockerHost | None:
    result = await db.execute(
        select(DockerHost).where(
            DockerHost.id == host_id, DockerHost.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def update_host(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID, data: DockerHostUpdate
) -> DockerHost | None:
    host = await get_host(db, tenant_id, host_id)
    if not host:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(host, field, value)
    await db.flush()
    return host


async def delete_host(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID
) -> bool:
    host = await get_host(db, tenant_id, host_id)
    if not host:
        return False
    await db.delete(host)
    await db.flush()
    return True


async def test_host_connection(
    db: AsyncSession, tenant_id: uuid.UUID, host_id: uuid.UUID
) -> dict:
    """Placeholder — will test Docker daemon connectivity."""
    raise NotImplementedError(
        "Docker host connection test not yet implemented. "
        "Will use Docker SDK to connect to tcp_url and verify access."
    )
```

- [ ] **Step 4: Create src/services/crash_event_service.py**

```python
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.crash_event import CrashEvent
from src.schemas.crash_event import CrashEventCreate, CrashStats, TopCrasher


async def create_crash_event(
    db: AsyncSession, tenant_id: uuid.UUID, data: CrashEventCreate
) -> CrashEvent:
    event = CrashEvent(
        tenant_id=tenant_id,
        docker_host_id=data.docker_host_id,
        container_name=data.container_name,
        container_id=data.container_id,
        image=data.image,
        exit_code=data.exit_code,
        logs=data.logs,
    )
    db.add(event)
    await db.flush()
    return event


async def list_crashes(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    severity: str | None = None,
    category: str | None = None,
) -> list[CrashEvent]:
    query = select(CrashEvent).where(CrashEvent.tenant_id == tenant_id)
    if severity:
        query = query.where(CrashEvent.severity == severity)
    if category:
        query = query.where(CrashEvent.category == category)
    query = query.order_by(CrashEvent.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_crash(
    db: AsyncSession, tenant_id: uuid.UUID, crash_id: uuid.UUID
) -> CrashEvent | None:
    result = await db.execute(
        select(CrashEvent).where(
            CrashEvent.id == crash_id, CrashEvent.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def get_crash_stats(db: AsyncSession, tenant_id: uuid.UUID) -> CrashStats:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    total = await db.execute(
        select(func.count()).select_from(CrashEvent).where(
            CrashEvent.tenant_id == tenant_id
        )
    )
    today = await db.execute(
        select(func.count()).select_from(CrashEvent).where(
            CrashEvent.tenant_id == tenant_id, CrashEvent.created_at >= day_ago
        )
    )
    cache_hits = await db.execute(
        select(func.count()).select_from(CrashEvent).where(
            CrashEvent.tenant_id == tenant_id, CrashEvent.cache_hit == True
        )
    )

    total_count = total.scalar() or 0
    cache_count = cache_hits.scalar() or 0

    return CrashStats(
        total_crashes=total_count,
        crashes_today=today.scalar() or 0,
        by_category={},  # Placeholder — aggregate query
        by_severity={},  # Placeholder — aggregate query
        cache_hit_rate=cache_count / total_count if total_count > 0 else 0.0,
        avg_resolution_time_ms=None,
    )


async def get_top_crashers(
    db: AsyncSession, tenant_id: uuid.UUID, limit: int = 10
) -> list[TopCrasher]:
    result = await db.execute(
        select(
            CrashEvent.container_name,
            func.count().label("crash_count"),
            func.max(CrashEvent.created_at).label("last_crash"),
        )
        .where(CrashEvent.tenant_id == tenant_id)
        .group_by(CrashEvent.container_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        TopCrasher(container_name=row[0], crash_count=row[1], last_crash=row[2])
        for row in result.all()
    ]
```

- [ ] **Step 5: Create src/services/api_key_service.py**

```python
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import ApiKey
from src.schemas.api_key import ApiKeyCreate


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, key_hash, key_prefix)."""
    key = f"dsk_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()
    key_prefix = key[:12]
    return key, key_hash, key_prefix


def verify_api_key(key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(key.encode(), key_hash.encode())


async def create_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, data: ApiKeyCreate
) -> tuple[ApiKey, str]:
    """Returns (api_key_model, full_key). Full key is only available at creation."""
    key, key_hash, key_prefix = generate_api_key()
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    api_key = ApiKey(
        tenant_id=tenant_id,
        created_by=user_id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=data.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()
    return api_key, key


async def list_api_keys(db: AsyncSession, tenant_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.tenant_id == tenant_id, ApiKey.is_active == True)
    )
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, key_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return False
    api_key.is_active = False
    await db.flush()
    return True


async def validate_api_key(db: AsyncSession, key: str) -> ApiKey | None:
    """Validate an API key and return the associated ApiKey model."""
    prefix = key[:12]
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True)
    )
    for api_key in result.scalars().all():
        if verify_api_key(key, api_key.key_hash):
            now = datetime.now(timezone.utc)
            if api_key.expires_at and api_key.expires_at < now:
                return None
            api_key.last_used_at = now
            await db.flush()
            return api_key
    return None
```

- [ ] **Step 6: Create src/services/notification_service.py**

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification_config import NotificationConfig
from src.schemas.notification import NotificationConfigUpdate


async def get_notification_configs(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[NotificationConfig]:
    result = await db.execute(
        select(NotificationConfig).where(NotificationConfig.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def upsert_notification_config(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    channel: str,
    data: NotificationConfigUpdate,
) -> NotificationConfig:
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.tenant_id == tenant_id,
            NotificationConfig.channel == channel,
        )
    )
    config = result.scalar_one_or_none()

    if config:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
    else:
        config = NotificationConfig(
            tenant_id=tenant_id,
            channel=channel,
            **data.model_dump(exclude_unset=True),
        )
        db.add(config)

    await db.flush()
    return config


async def test_notification(tenant_id: uuid.UUID, channel: str, message: str) -> dict:
    """Placeholder — will send a test notification via the specified channel."""
    raise NotImplementedError(
        f"Test notification for channel '{channel}' not yet implemented. "
        "Will send via Slack webhook / SMTP / Twilio based on channel type."
    )
```

- [ ] **Step 7: Create src/services/redis_stream.py**

```python
import json

import redis.asyncio as redis

from config.settings import settings

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def publish_crash_event(tenant_id: str, event_data: dict) -> str:
    """Publish a crash event to the tenant's Redis stream."""
    r = await get_redis()
    stream_key = f"crashes:{tenant_id}"
    message_id = await r.xadd(stream_key, {"data": json.dumps(event_data)})
    return message_id


async def consume_crash_events(
    tenant_id: str, consumer_group: str = "orchestrator", consumer_name: str = "worker-1"
) -> list[dict]:
    """Consume crash events from the tenant's Redis stream."""
    r = await get_redis()
    stream_key = f"crashes:{tenant_id}"

    # Create consumer group if it doesn't exist
    try:
        await r.xgroup_create(stream_key, consumer_group, id="0", mkstream=True)
    except redis.ResponseError:
        pass  # Group already exists

    messages = await r.xreadgroup(
        consumer_group, consumer_name, {stream_key: ">"}, count=10, block=5000
    )

    events = []
    for stream, msgs in messages:
        for msg_id, data in msgs:
            events.append({"id": msg_id, **json.loads(data["data"])})
            await r.xack(stream_key, consumer_group, msg_id)
    return events


async def publish_agent_event(tenant_id: str, event_data: dict) -> None:
    """Publish an event from an agent connection to the processing channel."""
    r = await get_redis()
    channel = f"agent:events:{tenant_id}"
    await r.publish(channel, json.dumps(event_data))
```

- [ ] **Step 8: Create src/services/crash_memory.py**

```python
class CrashMemory:
    """Qdrant vector cache for crash similarity matching.

    Placeholder — the user will implement:
    - Embedding crash logs with text-embedding-3-small
    - Storing in Qdrant collection 'crash_history'
    - Similarity search with threshold 0.92
    - Returning cached CrashAnalysis for matches
    """

    def __init__(self):
        pass

    async def find_similar(self, logs: str, threshold: float = 0.92) -> dict | None:
        """Search Qdrant for similar past crashes.

        Returns cached analysis dict if similarity > threshold, else None.
        """
        raise NotImplementedError(
            "Qdrant similarity search not yet implemented. "
            "Will use QdrantClient + OpenAIEmbeddings to find similar crash logs."
        )

    async def store(self, logs: str, analysis: dict) -> None:
        """Store crash logs + analysis in Qdrant for future matching."""
        raise NotImplementedError(
            "Qdrant storage not yet implemented. "
            "Will embed logs and store with analysis metadata."
        )
```

- [ ] **Step 9: Create src/services/metrics.py**

```python
from prometheus_client import Counter, Histogram, generate_latest, start_http_server

CRASHES_TOTAL = Counter(
    "sentinel_crashes_total",
    "Total container crashes detected",
    ["tenant_id", "container", "category"],
)

AGENT_LATENCY = Histogram(
    "sentinel_agent_latency_seconds",
    "Time spent in each agent",
    ["agent_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

RESTART_TOTAL = Counter(
    "sentinel_restarts_total",
    "Container restart attempts",
    ["tenant_id", "result"],
)

RESOLUTION_TYPE = Counter(
    "sentinel_resolution_type",
    "How crashes were resolved",
    ["type"],  # 'cache_hit' | 'llm_analysis' | 'auto_restart'
)

LLM_TOKENS = Counter(
    "sentinel_llm_tokens_total",
    "LLM tokens consumed",
    ["provider", "agent"],
)

CACHE_HIT = Counter(
    "sentinel_cache_hits_total",
    "Qdrant cache hits",
    ["tenant_id"],
)


def get_metrics() -> bytes:
    return generate_latest()


def start_metrics_server(port: int = 9091) -> None:
    """Start a standalone Prometheus metrics server (for worker process)."""
    start_http_server(port)
```

- [ ] **Step 10: Commit**

```bash
git add src/services/
git commit -m "feat: add service layer — auth, CRUD, Redis, metrics, crash memory"
```

---

## Phase 5: FastAPI Application

### Task 8: FastAPI App, Dependencies, and Middleware

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/app.py`
- Create: `src/api/deps.py`
- Create: `src/api/middleware.py`

- [ ] **Step 1: Create src/api/deps.py**

```python
import uuid
from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.models.tenant import Tenant
from src.models.user import User
from src.services.database import async_session_factory

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant inactive")
    return tenant
```

- [ ] **Step 2: Create src/api/middleware.py**

```python
import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

logger = logging.getLogger("sentinel.api")


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_url, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s %d %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response
```

- [ ] **Step 3: Create src/api/app.py**

```python
from fastapi import FastAPI

from src.api.middleware import setup_middleware
from src.api.routers import register_routers


def create_app() -> FastAPI:
    app = FastAPI(
        title="DockerSentinel API",
        description="Multi-Agent Docker Container Crash Monitor — SaaS Platform",
        version="0.1.0",
    )

    setup_middleware(app)
    register_routers(app)

    return app
```

- [ ] **Step 4: Create src/api/__init__.py as empty file**

- [ ] **Step 5: Commit**

```bash
git add src/api/__init__.py src/api/app.py src/api/deps.py src/api/middleware.py
git commit -m "feat: add FastAPI app factory, dependencies, and middleware"
```

---

### Task 9: All API Routers

**Files:**
- Create: `src/api/routers/__init__.py`
- Create: `src/api/routers/auth.py`
- Create: `src/api/routers/tenants.py`
- Create: `src/api/routers/docker_hosts.py`
- Create: `src/api/routers/crash_events.py`
- Create: `src/api/routers/api_keys.py`
- Create: `src/api/routers/notifications.py`
- Create: `src/api/routers/escalations.py`
- Create: `src/api/routers/dashboard.py`
- Create: `src/api/routers/websocket.py`
- Create: `src/api/routers/health.py`

- [ ] **Step 1: Create src/api/routers/health.py**

```python
from fastapi import APIRouter, Response

from src.services.metrics import get_metrics

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docker-sentinel-api"}


@router.get("/metrics")
async def prometheus_metrics():
    return Response(content=get_metrics(), media_type="text/plain")
```

- [ ] **Step 2: Create src/api/routers/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.auth import MeResponse, Token, TokenRefresh, UserResponse
from src.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/github")
async def github_login():
    """Initiate GitHub OAuth flow — returns redirect URL."""
    raise NotImplementedError(
        "GitHub OAuth not yet implemented. "
        "Will use authlib to redirect to GitHub authorization URL."
    )


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle GitHub OAuth callback — exchange code for tokens."""
    raise NotImplementedError(
        "GitHub OAuth callback not yet implemented. "
        "Will exchange code for access token, fetch user profile, "
        "call get_or_create_user_from_oauth, return JWT tokens."
    )


@router.get("/google")
async def google_login():
    """Initiate Google OAuth flow — returns redirect URL."""
    raise NotImplementedError(
        "Google OAuth not yet implemented. "
        "Will use authlib to redirect to Google authorization URL."
    )


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback — exchange code for tokens."""
    raise NotImplementedError(
        "Google OAuth callback not yet implemented. "
        "Will exchange code for access token, fetch user profile, "
        "call get_or_create_user_from_oauth, return JWT tokens."
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(body: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh an expired access token."""
    try:
        payload = auth_service.decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from e

    import uuid
    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])

    return Token(
        access_token=auth_service.create_access_token(user_id, tenant_id),
        refresh_token=auth_service.create_refresh_token(user_id, tenant_id),
    )


@router.post("/logout")
async def logout():
    """Logout — client should discard tokens."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from src.models.tenant import Tenant

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one()

    return MeResponse(
        user=UserResponse.model_validate(user),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
    )
```

- [ ] **Step 3: Create src/api/routers/tenants.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, get_tenant
from src.models.tenant import Tenant
from src.models.user import User
from src.schemas.tenant import (
    InviteMember,
    MemberResponse,
    TenantResponse,
    TenantUpdate,
)
from src.services import tenant_service

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(tenant: Tenant = Depends(get_tenant)):
    return tenant


@router.patch("/current", response_model=TenantResponse)
async def update_current_tenant(
    data: TenantUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    updated = await tenant_service.update_tenant(db, tenant.id, data.name)
    return updated


@router.get("/current/members", response_model=list[MemberResponse])
async def list_members(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await tenant_service.list_members(db, tenant.id)


@router.post("/current/members/invite")
async def invite_member(
    data: InviteMember,
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    raise NotImplementedError(
        "Member invitation not yet implemented. "
        "Will send email invitation and create pending user record."
    )
```

- [ ] **Step 4: Create src/api/routers/docker_hosts.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.tenant import Tenant
from src.schemas.docker_host import (
    ContainerInfo,
    DockerHostCreate,
    DockerHostResponse,
    DockerHostUpdate,
)
from src.services import docker_host_service

router = APIRouter(prefix="/api/v1/hosts", tags=["docker-hosts"])


@router.get("", response_model=list[DockerHostResponse])
async def list_hosts(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await docker_host_service.list_hosts(db, tenant.id)


@router.post("", response_model=DockerHostResponse, status_code=201)
async def create_host(
    data: DockerHostCreate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await docker_host_service.create_host(db, tenant.id, data)


@router.get("/{host_id}", response_model=DockerHostResponse)
async def get_host(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    host = await docker_host_service.get_host(db, tenant.id, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.patch("/{host_id}", response_model=DockerHostResponse)
async def update_host(
    host_id: uuid.UUID,
    data: DockerHostUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    host = await docker_host_service.update_host(db, tenant.id, host_id, data)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.delete("/{host_id}", status_code=204)
async def delete_host(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    deleted = await docker_host_service.delete_host(db, tenant.id, host_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Host not found")


@router.post("/{host_id}/test")
async def test_connection(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await docker_host_service.test_host_connection(db, tenant.id, host_id)


@router.get("/{host_id}/containers", response_model=list[ContainerInfo])
async def list_containers(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
):
    raise NotImplementedError(
        "Container listing not yet implemented. "
        "Will connect to Docker host and list running containers."
    )
```

- [ ] **Step 5: Create src/api/routers/crash_events.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.tenant import Tenant
from src.schemas.crash_event import CrashEventResponse, CrashStats, TopCrasher
from src.services import crash_event_service

router = APIRouter(prefix="/api/v1/crashes", tags=["crashes"])


@router.get("", response_model=list[CrashEventResponse])
async def list_crashes(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    severity: str | None = None,
    category: str | None = None,
):
    return await crash_event_service.list_crashes(
        db, tenant.id, limit, offset, severity, category
    )


@router.get("/stats", response_model=CrashStats)
async def get_stats(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await crash_event_service.get_crash_stats(db, tenant.id)


@router.get("/top-crashers", response_model=list[TopCrasher])
async def get_top_crashers(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    return await crash_event_service.get_top_crashers(db, tenant.id, limit)


@router.get("/{crash_id}", response_model=CrashEventResponse)
async def get_crash(
    crash_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    crash = await crash_event_service.get_crash(db, tenant.id, crash_id)
    if not crash:
        raise HTTPException(status_code=404, detail="Crash event not found")
    return crash
```

- [ ] **Step 6: Create src/api/routers/api_keys.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, get_tenant
from src.models.tenant import Tenant
from src.models.user import User
from src.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from src.services import api_key_service

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await api_key_service.list_api_keys(db, tenant.id)


@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    data: ApiKeyCreate,
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    api_key, full_key = await api_key_service.create_api_key(
        db, tenant.id, user.id, data
    )
    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key=full_key,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    revoked = await api_key_service.revoke_api_key(db, tenant.id, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
```

- [ ] **Step 7: Create src/api/routers/notifications.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.tenant import Tenant
from src.schemas.notification import (
    NotificationConfigResponse,
    NotificationConfigUpdate,
    TestNotificationRequest,
)
from src.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/config", response_model=list[NotificationConfigResponse])
async def get_notification_configs(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_notification_configs(db, tenant.id)


@router.put("/config/{channel}", response_model=NotificationConfigResponse)
async def update_notification_config(
    channel: str,
    data: NotificationConfigUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.upsert_notification_config(
        db, tenant.id, channel, data
    )


@router.post("/test/{channel}")
async def test_notification(
    channel: str,
    body: TestNotificationRequest,
    tenant: Tenant = Depends(get_tenant),
):
    return await notification_service.test_notification(tenant.id, channel, body.message)
```

- [ ] **Step 8: Create src/api/routers/escalations.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.escalation_rule import EscalationRule
from src.models.tenant import Tenant
from src.schemas.escalation import (
    EscalationRuleCreate,
    EscalationRuleResponse,
    EscalationRuleUpdate,
)

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])


@router.get("", response_model=list[EscalationRuleResponse])
async def list_rules(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationRule).where(EscalationRule.tenant_id == tenant.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=EscalationRuleResponse, status_code=201)
async def create_rule(
    data: EscalationRuleCreate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    rule = EscalationRule(tenant_id=tenant.id, **data.model_dump())
    db.add(rule)
    await db.flush()
    return rule


@router.patch("/{rule_id}", response_model=EscalationRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: EscalationRuleUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationRule).where(
            EscalationRule.id == rule_id, EscalationRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationRule).where(
            EscalationRule.id == rule_id, EscalationRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
```

- [ ] **Step 9: Create src/api/routers/dashboard.py**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.tenant import Tenant
from src.schemas.dashboard import DashboardSummary, MetricsResponse, TimelineResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    """AI-generated dashboard summary — placeholder."""
    raise NotImplementedError(
        "Dashboard AI summary not yet implemented. "
        "Will use Dashboard Agent (gpt-4o-mini) to generate natural language summary "
        "of recent crash activity, trends, and recommendations."
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Key operational metrics — placeholder."""
    raise NotImplementedError(
        "Dashboard metrics not yet implemented. "
        "Will query crash_events for MTTR, cache hit rate, restart success rate."
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
    period: str = Query("24h", regex="^(24h|7d|30d)$"),
):
    """Crash timeline data — placeholder."""
    raise NotImplementedError(
        "Crash timeline not yet implemented. "
        "Will aggregate crash_events by hour/day for the specified period."
    )
```

- [ ] **Step 10: Create src/api/routers/websocket.py**

```python
import json
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.services import api_key_service, redis_stream

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("sentinel.websocket")


@router.websocket("/api/v1/ws/agent")
async def agent_websocket(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for agent containers.

    Agents authenticate with API key, then stream Docker events.
    Events are published to Redis for the worker to consume.
    """
    db: AsyncSession
    async with (await get_db().__anext__()) if False else _placeholder():
        pass

    # Placeholder — full implementation will:
    # 1. Validate API key from query param
    # 2. Accept WebSocket connection
    # 3. Receive Docker events as JSON messages
    # 4. Publish each event to Redis stream for the tenant
    # 5. Handle disconnection gracefully

    await websocket.accept()
    try:
        # Validate API key
        # api_key = await api_key_service.validate_api_key(db, token)
        # if not api_key:
        #     await websocket.close(code=4001, reason="Invalid API key")
        #     return

        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            logger.info("Agent event received: %s", event.get("container_name", "unknown"))
            # await redis_stream.publish_agent_event(str(api_key.tenant_id), event)
    except WebSocketDisconnect:
        logger.info("Agent disconnected")


@router.websocket("/api/v1/ws/live")
async def live_feed(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for live crash feed in dashboard.

    Authenticated users receive real-time crash events for their tenant.
    """
    await websocket.accept()
    try:
        # Placeholder — full implementation will:
        # 1. Validate JWT from query param
        # 2. Subscribe to tenant's Redis pub/sub channel
        # 3. Forward crash events to WebSocket
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        logger.info("Live feed client disconnected")


class _placeholder:
    """Placeholder context manager."""
    async def __aenter__(self): return None
    async def __aexit__(self, *args): pass
```

- [ ] **Step 11: Create src/api/routers/__init__.py**

```python
from fastapi import FastAPI

from src.api.routers import (
    api_keys,
    auth,
    crash_events,
    dashboard,
    docker_hosts,
    escalations,
    health,
    notifications,
    tenants,
    websocket,
)


def register_routers(app: FastAPI) -> None:
    # Health + metrics (no auth)
    app.include_router(health.router)

    # Auth routes
    app.include_router(auth.router)

    # Authenticated API routes
    app.include_router(tenants.router)
    app.include_router(docker_hosts.router)
    app.include_router(crash_events.router)
    app.include_router(api_keys.router)
    app.include_router(notifications.router)
    app.include_router(escalations.router)
    app.include_router(dashboard.router)

    # WebSocket routes
    app.include_router(websocket.router)
```

- [ ] **Step 12: Commit**

```bash
git add src/api/
git commit -m "feat: add all FastAPI routers with endpoint definitions"
```

---

## Phase 6: Agents + Orchestrator + Worker

### Task 10: Agent Placeholders

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/fix_agent.py`
- Create: `src/agents/slack_agent.py`
- Create: `src/agents/email_agent.py`
- Create: `src/agents/call_agent.py`
- Create: `src/agents/dashboard_agent.py`

- [ ] **Step 1: Create src/agents/fix_agent.py**

```python
from src.schemas.crash_event import CrashAnalysis


class FixAgent:
    """Analyzes crash logs, determines root cause, decides if restart will fix it.

    Primary: Claude Haiku 4.5
    Fallback: OpenAI gpt-4o-mini
    Cache: Qdrant vector similarity (threshold 0.92)
    Output: CrashAnalysis (structured Pydantic model)
    """

    def __init__(self):
        # Placeholder — will initialize:
        # - ChatAnthropic(model="claude-haiku-4-5-20251001") as primary
        # - ChatOpenAI(model="gpt-4o-mini") as fallback
        # - primary.with_fallbacks([fallback])
        # - llm.with_structured_output(CrashAnalysis)
        # - CrashMemory() for Qdrant cache
        pass

    async def analyze(self, crash_event: dict) -> CrashAnalysis:
        """Analyze a crash event and return structured diagnosis.

        Flow:
        1. Check Qdrant cache for similar past crashes (< 100ms)
        2. If cache hit (similarity > 0.92): return cached analysis
        3. If no match: call LLM with crash logs + context
        4. Store new analysis in Qdrant for future matching
        5. Return CrashAnalysis
        """
        raise NotImplementedError(
            "Fix Agent analysis not yet implemented. "
            "Will use Claude Haiku with structured output to analyze crash logs. "
            "Checks Qdrant cache first, falls back to LLM, stores result."
        )
```

- [ ] **Step 2: Create src/agents/slack_agent.py**

```python
class SlackAgent:
    """Sends immediate crash alerts to Slack channels via webhooks.

    Uses Block Kit formatting for rich, readable notifications.
    Cost: $0 — Free forever.
    """

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url

    async def notify(self, crash_event: dict, analysis: dict) -> bool:
        """Send a Slack notification with crash details and analysis.

        Message includes: container name, exit code, severity, root cause,
        and suggested fixes in Block Kit format.
        """
        raise NotImplementedError(
            "Slack notification not yet implemented. "
            "Will use httpx to POST Block Kit formatted message to webhook URL."
        )
```

- [ ] **Step 3: Create src/agents/email_agent.py**

```python
class EmailAgent:
    """Sends comprehensive crash reports with logs, AI analysis, and fix suggestions.

    Uses SendGrid / Gmail SMTP with Jinja2 templates.
    Cost: $0 — SendGrid free tier (100/day).
    """

    def __init__(self):
        pass

    async def send(
        self, crash_event: dict, analysis: dict, recipient_email: str
    ) -> bool:
        """Send detailed crash report email.

        Email contents: container name, image, exit code, last 100 log lines,
        timestamp + uptime, AI-generated root cause, suggested fixes,
        restart outcome, and dashboard link.
        """
        raise NotImplementedError(
            "Email sending not yet implemented. "
            "Will use Jinja2 to render crash_email.html template, "
            "then send via SendGrid API or SMTP."
        )
```

- [ ] **Step 4: Create src/agents/call_agent.py**

```python
class CallAgent:
    """Automated voice calls when multiple containers crash — the nuclear option.

    Uses Twilio Voice API with TwiML.
    Trigger: >=2 containers crash within a 5-minute sliding window.
    Cost: ~$0.014/min.
    """

    def __init__(self):
        pass

    async def escalate(
        self, crash_events: list[dict], on_call_phone: str
    ) -> bool:
        """Make an automated voice call to the on-call engineer.

        Uses Claude Haiku to generate a 20-second urgent voice script,
        then places the call via Twilio with TwiML.
        """
        raise NotImplementedError(
            "Voice call escalation not yet implemented. "
            "Will use Claude Haiku to generate voice script, "
            "then Twilio REST client to place the call."
        )
```

- [ ] **Step 5: Create src/agents/dashboard_agent.py**

```python
class DashboardAgent:
    """Generates AI-powered summaries for the stakeholder dashboard.

    Uses gpt-4o-mini for natural language daily/weekly summaries.
    Cost: Included in OpenAI budget.
    """

    def __init__(self):
        pass

    async def generate_summary(
        self, crash_events: list[dict], period: str = "24h"
    ) -> str:
        """Generate a natural language summary of recent crash activity.

        Covers: total crashes, most affected containers, common root causes,
        resolution effectiveness, trends, and recommendations.
        """
        raise NotImplementedError(
            "Dashboard AI summary not yet implemented. "
            "Will use gpt-4o-mini to summarize recent crash events "
            "into a natural language report for stakeholders."
        )
```

- [ ] **Step 6: Create src/agents/__init__.py**

```python
from src.agents.call_agent import CallAgent
from src.agents.dashboard_agent import DashboardAgent
from src.agents.email_agent import EmailAgent
from src.agents.fix_agent import FixAgent
from src.agents.slack_agent import SlackAgent

__all__ = ["FixAgent", "SlackAgent", "EmailAgent", "CallAgent", "DashboardAgent"]
```

- [ ] **Step 7: Commit**

```bash
git add src/agents/
git commit -m "feat: add 5 agent placeholders — fix, slack, email, call, dashboard"
```

---

### Task 11: LangGraph Orchestrator

**Files:**
- Create: `src/orchestrator/__init__.py`
- Create: `src/orchestrator/state.py`
- Create: `src/orchestrator/nodes.py`
- Create: `src/orchestrator/graph.py`

- [ ] **Step 1: Create src/orchestrator/state.py**

```python
from typing import TypedDict


class CrashState(TypedDict):
    """State that flows through the LangGraph orchestrator."""

    # Input
    tenant_id: str
    crash_event: dict

    # Analysis (populated by Fix Agent)
    analysis: dict | None
    cache_hit: bool

    # Actions taken
    restart_attempted: bool
    restart_success: bool
    slack_sent: bool
    email_sent: bool
    call_triggered: bool

    # Context
    recent_crash_count: int
    docker_host_id: str
```

- [ ] **Step 2: Create src/orchestrator/nodes.py**

```python
from src.orchestrator.state import CrashState


async def analyze_crash(state: CrashState) -> dict:
    """Node: Run Fix Agent to analyze the crash.

    Checks Qdrant cache first, then calls LLM if needed.
    """
    raise NotImplementedError(
        "analyze_crash node not yet implemented. "
        "Will instantiate FixAgent, call analyze(crash_event), "
        "and return updated state with analysis results."
    )


async def attempt_restart(state: CrashState) -> dict:
    """Node: Attempt to restart the crashed container."""
    raise NotImplementedError(
        "attempt_restart node not yet implemented. "
        "Will use Docker SDK to restart the container, "
        "verify it's running, and update state."
    )


async def notify_slack(state: CrashState) -> dict:
    """Node: Send Slack notification."""
    raise NotImplementedError(
        "notify_slack node not yet implemented. "
        "Will look up tenant notification config, "
        "instantiate SlackAgent, and call notify()."
    )


async def send_email(state: CrashState) -> dict:
    """Node: Send detailed email report."""
    raise NotImplementedError(
        "send_email node not yet implemented. "
        "Will look up tenant notification config + container owner, "
        "instantiate EmailAgent, and call send()."
    )


async def make_call(state: CrashState) -> dict:
    """Node: Make voice call for critical multi-crash escalation."""
    raise NotImplementedError(
        "make_call node not yet implemented. "
        "Will look up tenant escalation config, "
        "instantiate CallAgent, and call escalate()."
    )


async def log_event(state: CrashState) -> dict:
    """Node: Log the crash event and all actions to the database."""
    raise NotImplementedError(
        "log_event node not yet implemented. "
        "Will update crash_event record in PostgreSQL with analysis results "
        "and action flags, then update Prometheus metrics."
    )


def should_restart(state: CrashState) -> str:
    """Conditional edge: decide whether to attempt restart or go straight to notification."""
    analysis = state.get("analysis")
    if analysis and analysis.get("restart_likely_fixes"):
        return "attempt_restart"
    return "notify_slack"


def check_restart_result(state: CrashState) -> str:
    """Conditional edge: after restart, check if it succeeded."""
    if state.get("restart_success"):
        return "log"
    return "notify_slack"


def check_multi_crash(state: CrashState) -> str:
    """Conditional edge: after email, check if multi-crash threshold is met."""
    if state.get("recent_crash_count", 0) >= 2:
        return "make_call"
    return "log"
```

- [ ] **Step 3: Create src/orchestrator/graph.py**

```python
from langgraph.graph import END, StateGraph

from src.orchestrator.nodes import (
    analyze_crash,
    attempt_restart,
    check_multi_crash,
    check_restart_result,
    log_event,
    make_call,
    notify_slack,
    send_email,
    should_restart,
)
from src.orchestrator.state import CrashState


def build_crash_workflow() -> StateGraph:
    """Build the LangGraph state machine for crash event processing.

    Decision Flow:
        ANALYZE → restart_likely? → RESTART → success? → LOG
                                                       → SLACK → EMAIL → multi_crash? → CALL → LOG
                → code/config issue → SLACK → EMAIL → multi_crash? → CALL → LOG
                                                                    → LOG
    """
    workflow = StateGraph(CrashState)

    # Add nodes
    workflow.add_node("analyze", analyze_crash)
    workflow.add_node("restart", attempt_restart)
    workflow.add_node("slack", notify_slack)
    workflow.add_node("email", send_email)
    workflow.add_node("call", make_call)
    workflow.add_node("log", log_event)

    # Entry point
    workflow.set_entry_point("analyze")

    # Conditional: after analysis, decide restart vs notify
    workflow.add_conditional_edges(
        "analyze",
        should_restart,
        {"attempt_restart": "restart", "notify_slack": "slack"},
    )

    # Conditional: after restart, check result
    workflow.add_conditional_edges(
        "restart",
        check_restart_result,
        {"log": "log", "notify_slack": "slack"},
    )

    # Slack always flows to email
    workflow.add_edge("slack", "email")

    # Conditional: after email, check multi-crash threshold
    workflow.add_conditional_edges(
        "email",
        check_multi_crash,
        {"make_call": "call", "log": "log"},
    )

    # Call flows to log
    workflow.add_edge("call", "log")

    # Log is the terminal node
    workflow.add_edge("log", END)

    return workflow


# Compile the workflow for use
crash_workflow = build_crash_workflow().compile()
```

- [ ] **Step 4: Create src/orchestrator/__init__.py**

```python
from src.orchestrator.graph import crash_workflow
from src.orchestrator.state import CrashState

__all__ = ["crash_workflow", "CrashState"]
```

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/
git commit -m "feat: add LangGraph orchestrator with state machine and conditional edges"
```

---

### Task 12: Listener + Worker + Agent Container

**Files:**
- Create: `src/listener/__init__.py`
- Create: `src/listener/docker_monitor.py`
- Create: `src/listener/manager.py`
- Create: `src/worker/__init__.py`
- Create: `src/worker/main.py`
- Create: `src/agent_container/main.py`
- Create: `src/agent_container/requirements.txt`

- [ ] **Step 1: Create src/listener/docker_monitor.py**

```python
import logging

logger = logging.getLogger("sentinel.listener")


class DockerMonitor:
    """Connects to a remote Docker daemon and listens for crash events.

    Uses Docker SDK for Python over TCP/TLS.
    Captures 'die', 'oom', 'kill' events and pulls last 200 log lines.
    """

    def __init__(self, host_url: str, tls_config: dict | None = None):
        self.host_url = host_url
        self.tls_config = tls_config
        self._running = False

    async def start(self) -> None:
        """Start listening for Docker events on the remote daemon."""
        raise NotImplementedError(
            "Docker event listener not yet implemented. "
            "Will use docker.DockerClient(base_url=host_url) to connect, "
            "then client.events(filters={'event': ['die', 'oom', 'kill']}) "
            "to stream events. Each event triggers CrashEvent creation."
        )

    async def stop(self) -> None:
        """Stop listening and disconnect."""
        self._running = False
        logger.info("Stopped monitoring %s", self.host_url)
```

- [ ] **Step 2: Create src/listener/manager.py**

```python
import logging

logger = logging.getLogger("sentinel.listener.manager")


class ListenerManager:
    """Manages Docker listeners across all tenants and hosts.

    Polls PostgreSQL for active docker_hosts records.
    Spawns/stops async listeners as hosts are added/removed.
    Handles reconnection on failure.
    """

    def __init__(self):
        self._listeners: dict[str, object] = {}  # host_id -> DockerMonitor

    async def sync_listeners(self) -> None:
        """Poll DB for active hosts and sync listener state.

        - New hosts: spawn listener
        - Removed/deactivated hosts: stop listener
        - Failed listeners: attempt reconnection
        """
        raise NotImplementedError(
            "Listener sync not yet implemented. "
            "Will query docker_hosts for active TCP hosts, "
            "compare with running listeners, and spawn/stop as needed."
        )

    async def start(self) -> None:
        """Start the listener manager loop."""
        raise NotImplementedError(
            "Listener manager start not yet implemented. "
            "Will run sync_listeners() on a polling interval (e.g., every 30s)."
        )

    async def stop(self) -> None:
        """Stop all listeners gracefully."""
        for host_id, listener in self._listeners.items():
            logger.info("Stopping listener for host %s", host_id)
        self._listeners.clear()
```

- [ ] **Step 3: Create src/listener/__init__.py as empty file**

- [ ] **Step 4: Create src/worker/main.py**

```python
import asyncio
import logging
import signal

from src.listener.manager import ListenerManager
from src.services.metrics import start_metrics_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("sentinel.worker")


async def consume_crash_events():
    """Main loop: consume crash events from Redis and run through LangGraph orchestrator."""
    raise NotImplementedError(
        "Crash event consumer not yet implemented. "
        "Will poll all tenant Redis streams, deserialize CrashEvents, "
        "run each through crash_workflow.ainvoke(), and handle results."
    )


async def main():
    logger.info("Starting DockerSentinel Worker...")

    # Start Prometheus metrics server for worker
    start_metrics_server(port=9091)

    # Start listener manager (manages Docker connections)
    manager = ListenerManager()

    # Handle shutdown gracefully
    shutdown_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

    logger.info("Worker ready. Waiting for crash events...")

    # Placeholder — will run:
    # await asyncio.gather(
    #     manager.start(),
    #     consume_crash_events(),
    # )

    await shutdown_event.wait()
    await manager.stop()
    logger.info("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Create src/worker/__init__.py as empty file**

- [ ] **Step 6: Create src/agent_container/main.py**

```python
"""DockerSentinel Agent — Lightweight container that monitors local Docker events.

Usage:
    docker run -v /var/run/docker.sock:/var/run/docker.sock \
        dockersentinel/agent --token YOUR_API_KEY --url wss://your-sentinel.com/api/v1/ws/agent

The agent:
1. Connects to the local Docker socket
2. Authenticates to DockerSentinel platform via API key
3. Listens for die/oom/kill events
4. Streams crash events back to the platform via WebSocket
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("sentinel.agent")


def main():
    parser = argparse.ArgumentParser(description="DockerSentinel Agent")
    parser.add_argument("--token", required=True, help="API key for authentication")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/api/v1/ws/agent",
        help="WebSocket URL of the DockerSentinel platform",
    )
    parser.add_argument(
        "--docker-socket",
        default="/var/run/docker.sock",
        help="Path to Docker socket",
    )
    args = parser.parse_args()

    logger.info("DockerSentinel Agent starting...")
    logger.info("Platform URL: %s", args.url)
    logger.info("Docker socket: %s", args.docker_socket)

    # Placeholder — full implementation will:
    # 1. Connect to local Docker socket via Docker SDK
    # 2. Establish WebSocket connection to platform (with API key auth)
    # 3. Listen for Docker die/oom/kill events
    # 4. For each event: pull last 200 log lines, construct CrashEvent JSON
    # 5. Send CrashEvent over WebSocket
    # 6. Handle reconnection on disconnect
    raise NotImplementedError(
        "Agent event streaming not yet implemented. "
        "Will use docker.DockerClient for local events "
        "and websockets library to stream to platform."
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Create src/agent_container/requirements.txt**

```
docker>=7.0.0
websockets>=12.0
```

- [ ] **Step 8: Commit**

```bash
git add src/listener/ src/worker/ src/agent_container/
git commit -m "feat: add Docker listener, worker process, and agent container"
```

---

## Phase 7: Templates, Scripts, Tests, CI

### Task 13: Email Template + Scripts

**Files:**
- Create: `src/templates/crash_email.html`
- Create: `scripts/simulate_crash.py`
- Create: `scripts/seed_db.py`
- Create: `scripts/generate_api_key.py`

- [ ] **Step 1: Create src/templates/crash_email.html**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .header { background: #dc2626; color: white; padding: 20px 24px; }
        .header h1 { margin: 0; font-size: 20px; }
        .body { padding: 24px; }
        .field { margin-bottom: 16px; }
        .label { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; margin-bottom: 4px; }
        .value { font-size: 14px; color: #111827; }
        .severity { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .severity-critical { background: #fef2f2; color: #dc2626; }
        .severity-high { background: #fff7ed; color: #ea580c; }
        .severity-medium { background: #fefce8; color: #ca8a04; }
        .severity-low { background: #f0fdf4; color: #16a34a; }
        .logs { background: #1f2937; color: #e5e7eb; padding: 16px; border-radius: 6px; font-family: monospace; font-size: 12px; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
        .suggestions { padding-left: 20px; }
        .suggestions li { margin-bottom: 8px; color: #374151; }
        .footer { padding: 16px 24px; background: #f9fafb; border-top: 1px solid #e5e7eb; text-align: center; }
        .footer a { color: #2563eb; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Container Crash: {{ event.container_name }}</h1>
        </div>
        <div class="body">
            <div class="field">
                <div class="label">Container</div>
                <div class="value">{{ event.container_name }} ({{ event.container_id[:12] }})</div>
            </div>
            <div class="field">
                <div class="label">Image</div>
                <div class="value">{{ event.image }}</div>
            </div>
            <div class="field">
                <div class="label">Exit Code</div>
                <div class="value">{{ event.exit_code }}</div>
            </div>
            <div class="field">
                <div class="label">Severity</div>
                <div class="value"><span class="severity severity-{{ analysis.severity }}">{{ analysis.severity | upper }}</span></div>
            </div>
            <div class="field">
                <div class="label">Root Cause</div>
                <div class="value">{{ analysis.root_cause }}</div>
            </div>
            <div class="field">
                <div class="label">Category</div>
                <div class="value">{{ analysis.category }}</div>
            </div>
            {% if analysis.suggestions %}
            <div class="field">
                <div class="label">Suggested Fixes</div>
                <ol class="suggestions">
                    {% for suggestion in analysis.suggestions %}
                    <li>{{ suggestion }}</li>
                    {% endfor %}
                </ol>
            </div>
            {% endif %}
            {% if summary %}
            <div class="field">
                <div class="label">AI Summary</div>
                <div class="value">{{ summary }}</div>
            </div>
            {% endif %}
            {% if event.logs %}
            <div class="field">
                <div class="label">Last Log Lines</div>
                <div class="logs">{{ event.logs }}</div>
            </div>
            {% endif %}
        </div>
        <div class="footer">
            <a href="{{ dashboard_url }}">View in Dashboard</a>
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 2: Create scripts/simulate_crash.py**

```python
"""Simulate a Docker container crash for testing the pipeline.

Usage: python scripts/simulate_crash.py --tenant-id <uuid> --host-id <uuid>
"""

import argparse
import asyncio
import uuid

from src.schemas.crash_event import CrashEventCreate
from src.services.redis_stream import publish_crash_event


async def simulate(tenant_id: str, host_id: str):
    event = CrashEventCreate(
        docker_host_id=uuid.UUID(host_id),
        container_name="payment-service",
        container_id="abc123def456",
        image="myorg/payment:latest",
        exit_code=137,
        logs="2026-04-12 10:00:01 ERROR: Out of memory\n"
        "2026-04-12 10:00:01 FATAL: Cannot allocate memory for buffer pool\n"
        "2026-04-12 10:00:01 Container killed by OOM killer",
    )

    message_id = await publish_crash_event(tenant_id, event.model_dump(mode="json"))
    print(f"Crash event published to Redis: {message_id}")
    print(f"Tenant: {tenant_id}")
    print(f"Container: {event.container_name} (exit code {event.exit_code})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a Docker crash event")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--host-id", required=True, help="Docker host UUID")
    args = parser.parse_args()
    asyncio.run(simulate(args.tenant_id, args.host_id))
```

- [ ] **Step 3: Create scripts/seed_db.py**

```python
"""Seed the database with test data for development.

Usage: python scripts/seed_db.py
"""

import asyncio
import uuid

from sqlalchemy import text

from src.models.tenant import Tenant
from src.models.user import User
from src.models.docker_host import DockerHost
from src.services.database import async_session_factory


async def seed():
    async with async_session_factory() as db:
        # Create test tenant
        tenant = Tenant(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Workspace",
            slug="test-workspace",
        )
        db.add(tenant)

        # Create test user
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            tenant_id=tenant.id,
            email="test@example.com",
            name="Test User",
            role="owner",
            oauth_provider="github",
            oauth_provider_id="12345",
        )
        db.add(user)

        # Create test Docker host (TCP mode)
        host = DockerHost(
            id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            tenant_id=tenant.id,
            name="Dev Server",
            connection_mode="tcp",
            tcp_url="tcp://localhost:2375",
            status="connected",
        )
        db.add(host)

        await db.commit()
        print("Database seeded successfully!")
        print(f"  Tenant: {tenant.name} ({tenant.id})")
        print(f"  User: {user.email} ({user.id})")
        print(f"  Host: {host.name} ({host.id})")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 4: Create scripts/generate_api_key.py**

```python
"""Generate an API key for a tenant.

Usage: python scripts/generate_api_key.py --tenant-id <uuid> --name "My Agent Key"
"""

import argparse
import asyncio
import uuid

from src.services.api_key_service import create_api_key
from src.schemas.api_key import ApiKeyCreate
from src.services.database import async_session_factory


async def generate(tenant_id: str, name: str):
    async with async_session_factory() as db:
        data = ApiKeyCreate(name=name, scopes=["agent"])
        api_key, full_key = await create_api_key(
            db, uuid.UUID(tenant_id), None, data
        )
        await db.commit()

        print(f"API Key created successfully!")
        print(f"  Name: {api_key.name}")
        print(f"  Key: {full_key}")
        print(f"  Prefix: {api_key.key_prefix}")
        print(f"\n  Save this key — it cannot be retrieved again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an API key")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--name", required=True, help="Key name/description")
    args = parser.parse_args()
    asyncio.run(generate(args.tenant_id, args.name))
```

- [ ] **Step 5: Commit**

```bash
git add src/templates/ scripts/
git commit -m "feat: add email template and utility scripts"
```

---

### Task 14: Tests + CI

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/test_auth.py`
- Create: `tests/test_api/test_hosts.py`
- Create: `tests/test_api/test_crashes.py`
- Create: `tests/test_services/__init__.py`
- Create: `tests/test_services/test_crash_event.py`
- Create: `tests/test_services/test_orchestrator.py`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create tests/conftest.py**

```python
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.services.auth_service import create_access_token

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    token = create_access_token(TEST_USER_ID, TEST_TENANT_ID)
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 2: Create tests/test_api/test_auth.py**

```python
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_github_login_not_implemented(client):
    response = await client.get("/api/v1/auth/github")
    assert response.status_code == 500  # NotImplementedError
```

- [ ] **Step 3: Create tests/test_api/test_hosts.py**

```python
import pytest


@pytest.mark.asyncio
async def test_list_hosts_requires_auth(client):
    response = await client.get("/api/v1/hosts")
    assert response.status_code == 403
```

- [ ] **Step 4: Create tests/test_api/test_crashes.py**

```python
import pytest


@pytest.mark.asyncio
async def test_list_crashes_requires_auth(client):
    response = await client.get("/api/v1/crashes")
    assert response.status_code == 403
```

- [ ] **Step 5: Create tests/test_services/test_crash_event.py**

```python
import pytest

from src.schemas.crash_event import CrashAnalysis


def test_crash_analysis_schema():
    analysis = CrashAnalysis(
        restart_likely_fixes=True,
        root_cause="Out of memory — container exceeded 512MB limit",
        severity="high",
        category="oom",
        suggestions=["Increase memory limit to 1GB", "Check for memory leaks"],
        confidence=0.92,
    )
    assert analysis.restart_likely_fixes is True
    assert analysis.severity == "high"
    assert len(analysis.suggestions) == 2


def test_crash_analysis_validation():
    with pytest.raises(Exception):
        CrashAnalysis()  # Missing required fields
```

- [ ] **Step 6: Create tests/test_services/test_orchestrator.py**

```python
import pytest

from src.orchestrator.nodes import should_restart, check_multi_crash, check_restart_result


def test_should_restart_true():
    state = {"analysis": {"restart_likely_fixes": True}}
    assert should_restart(state) == "attempt_restart"


def test_should_restart_false():
    state = {"analysis": {"restart_likely_fixes": False}}
    assert should_restart(state) == "notify_slack"


def test_should_restart_no_analysis():
    state = {"analysis": None}
    assert should_restart(state) == "notify_slack"


def test_check_restart_success():
    state = {"restart_success": True}
    assert check_restart_result(state) == "log"


def test_check_restart_failure():
    state = {"restart_success": False}
    assert check_restart_result(state) == "notify_slack"


def test_check_multi_crash_above_threshold():
    state = {"recent_crash_count": 3}
    assert check_multi_crash(state) == "make_call"


def test_check_multi_crash_below_threshold():
    state = {"recent_crash_count": 1}
    assert check_multi_crash(state) == "log"
```

- [ ] **Step 7: Create all __init__.py files**

Create empty `tests/__init__.py`, `tests/test_api/__init__.py`, `tests/test_services/__init__.py`.

- [ ] **Step 8: Create .github/workflows/ci.yml**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff
      - run: ruff check src/ tests/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ".[dev]"
      - run: pytest tests/ -v --tb=short

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t docker-sentinel:test .
      - run: docker build -t docker-sentinel-agent:test -f Dockerfile.agent .
```

- [ ] **Step 9: Commit**

```bash
git add tests/ .github/
git commit -m "feat: add test suite and GitHub Actions CI"
```

---

## Phase 8: Frontend (Next.js)

### Task 15: Initialize Next.js + Shadcn/ui

**Files:**
- Create: `frontend/` (via npx create-next-app)
- Create: `frontend/.env.local.example`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create Next.js app**

```bash
cd c:/docker-sentinel
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

- [ ] **Step 2: Initialize Shadcn/ui**

```bash
cd c:/docker-sentinel/frontend
npx shadcn@latest init -d
```

- [ ] **Step 3: Install core Shadcn components**

```bash
cd c:/docker-sentinel/frontend
npx shadcn@latest add button card input label table badge separator dropdown-menu sheet avatar tabs dialog alert toast
```

- [ ] **Step 4: Create frontend/.env.local.example**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=DockerSentinel
```

- [ ] **Step 5: Create frontend/Dockerfile**

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 6: Update frontend/next.config.ts for standalone output**

Replace the contents of `frontend/next.config.ts` with:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 7: Commit**

```bash
cd c:/docker-sentinel
git add frontend/
git commit -m "feat: initialize Next.js with Shadcn/ui and Tailwind"
```

---

### Task 16: Frontend Lib + Hooks

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/utils.ts` (may already exist from Shadcn init)
- Create: `frontend/src/hooks/use-auth.ts`
- Create: `frontend/src/hooks/use-crashes.ts`
- Create: `frontend/src/hooks/use-websocket.ts`

- [ ] **Step 1: Create frontend/src/lib/api.ts**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // TODO: Attempt token refresh
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  put<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  delete(path: string) {
    return this.request(path, { method: "DELETE" });
  }
}

export const api = new ApiClient(API_URL);
```

- [ ] **Step 2: Create frontend/src/lib/auth.ts**

```typescript
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
```

- [ ] **Step 3: Create frontend/src/hooks/use-auth.ts**

```typescript
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { isAuthenticated, clearTokens } from "@/lib/auth";

interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: string;
}

interface AuthState {
  user: User | null;
  tenantName: string | null;
  loading: boolean;
  logout: () => void;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [tenantName, setTenantName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      setLoading(false);
      return;
    }

    api
      .get<{ user: User; tenant_name: string }>("/api/v1/auth/me")
      .then((data) => {
        setUser(data.user);
        setTenantName(data.tenant_name);
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = () => {
    clearTokens();
    setUser(null);
    window.location.href = "/login";
  };

  return { user, tenantName, loading, logout };
}
```

- [ ] **Step 4: Create frontend/src/hooks/use-crashes.ts**

```typescript
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CrashEvent {
  id: string;
  container_name: string;
  image: string;
  exit_code: number | null;
  severity: string | null;
  category: string | null;
  root_cause: string | null;
  created_at: string;
}

export function useCrashes(limit = 50) {
  const [crashes, setCrashes] = useState<CrashEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CrashEvent[]>(`/api/v1/crashes?limit=${limit}`)
      .then(setCrashes)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit]);

  return { crashes, loading, error };
}
```

- [ ] **Step 5: Create frontend/src/hooks/use-websocket.ts**

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";

const WS_URL = process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://localhost:8000";

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const [lastEvent, setLastEvent] = useState<unknown>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;

    const socket = new WebSocket(`${WS_URL}/api/v1/ws/live?token=${token}`);

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        setLastEvent(JSON.parse(event.data));
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.current = socket;

    return () => {
      socket.close();
    };
  }, []);

  return { lastEvent, connected };
}
```

- [ ] **Step 6: Commit**

```bash
cd c:/docker-sentinel
git add frontend/src/lib/ frontend/src/hooks/
git commit -m "feat: add API client, auth helpers, and React hooks"
```

---

### Task 17: Frontend Layout Components

**Files:**
- Create: `frontend/src/components/layout/sidebar.tsx`
- Create: `frontend/src/components/layout/header.tsx`
- Create: `frontend/src/components/layout/nav-links.tsx`

- [ ] **Step 1: Create frontend/src/components/layout/nav-links.tsx**

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard", icon: "LayoutDashboard" },
  { href: "/crashes", label: "Crashes", icon: "AlertTriangle" },
  { href: "/hosts", label: "Docker Hosts", icon: "Server" },
  { href: "/settings", label: "Settings", icon: "Settings" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            pathname === link.href
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          )}
        >
          <span>{link.label}</span>
        </Link>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Create frontend/src/components/layout/sidebar.tsx**

```typescript
import { NavLinks } from "./nav-links";

export function Sidebar() {
  return (
    <aside className="hidden w-64 border-r bg-background lg:block">
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-lg font-bold">DockerSentinel</h1>
      </div>
      <div className="px-4 py-6">
        <NavLinks />
      </div>
    </aside>
  );
}
```

- [ ] **Step 3: Create frontend/src/components/layout/header.tsx**

```typescript
"use client";

import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export function Header() {
  const { user, tenantName, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b px-6">
      <div>
        <span className="text-sm text-muted-foreground">{tenantName}</span>
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-sm">{user.name || user.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              Logout
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd c:/docker-sentinel
git add frontend/src/components/layout/
git commit -m "feat: add sidebar, header, and navigation components"
```

---

### Task 18: Frontend Pages

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/app/(auth)/callback/page.tsx`
- Create: `frontend/src/app/(dashboard)/layout.tsx`
- Create: `frontend/src/app/(dashboard)/page.tsx`
- Create: `frontend/src/app/(dashboard)/crashes/page.tsx`
- Create: `frontend/src/app/(dashboard)/crashes/[id]/page.tsx`
- Create: `frontend/src/app/(dashboard)/hosts/page.tsx`
- Create: `frontend/src/app/(dashboard)/hosts/new/page.tsx`
- Create: `frontend/src/app/(dashboard)/settings/page.tsx`
- Create: `frontend/src/app/(dashboard)/settings/notifications/page.tsx`
- Create: `frontend/src/app/(dashboard)/settings/api-keys/page.tsx`
- Create: `frontend/src/app/(dashboard)/settings/escalations/page.tsx`
- Create: `frontend/src/app/(dashboard)/settings/members/page.tsx`
- Create: `frontend/src/app/(dashboard)/onboarding/page.tsx`

- [ ] **Step 1: Update frontend/src/app/layout.tsx**

Replace with:

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DockerSentinel",
  description: "Multi-Agent Docker Container Crash Monitor",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Update frontend/src/app/page.tsx**

Replace with redirect logic:

```typescript
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/login");
}
```

- [ ] **Step 3: Create frontend/src/app/(auth)/login/page.tsx**

```typescript
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">DockerSentinel</CardTitle>
          <CardDescription>
            Multi-Agent Docker Container Crash Monitor
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <a href={`${API_URL}/api/v1/auth/github`}>
            <Button className="w-full" variant="outline">
              Continue with GitHub
            </Button>
          </a>
          <a href={`${API_URL}/api/v1/auth/google`}>
            <Button className="w-full" variant="outline">
              Continue with Google
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: Create frontend/src/app/(auth)/callback/page.tsx**

```typescript
"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { setTokens } from "@/lib/auth";

export default function CallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (accessToken && refreshToken) {
      setTokens(accessToken, refreshToken);
      router.push("/");
    } else {
      router.push("/login");
    }
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing in...</p>
    </div>
  );
}
```

- [ ] **Step 5: Create frontend/src/app/(dashboard)/layout.tsx**

```typescript
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create frontend/src/app/(dashboard)/page.tsx**

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Crashes (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Auto-Restarts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cache Hit Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Hosts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>AI Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Dashboard AI summary will appear here once the Dashboard Agent is implemented.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Crash Timeline</CardTitle>
        </CardHeader>
        <CardContent className="h-64 flex items-center justify-center">
          <p className="text-muted-foreground">Chart will be rendered here</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 7: Create remaining dashboard pages**

Create each file with a simple placeholder page component. These are shell pages — the user will wire up data fetching later.

`frontend/src/app/(dashboard)/crashes/page.tsx`:
```typescript
export default function CrashesPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Crash Events</h2>
      <p className="text-muted-foreground">
        Crash events table with filtering will be implemented here.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/crashes/[id]/page.tsx`:
```typescript
export default function CrashDetailPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Crash Detail</h2>
      <p className="text-muted-foreground">
        Detailed crash view with logs, analysis, and actions will be implemented here.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/hosts/page.tsx`:
```typescript
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HostsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Docker Hosts</h2>
        <Link href="/hosts/new">
          <Button>Add Host</Button>
        </Link>
      </div>
      <p className="text-muted-foreground">
        Docker hosts with connection status will be listed here.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/hosts/new/page.tsx`:
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AddHostPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">Add Docker Host</h2>
      <Card>
        <CardHeader>
          <CardTitle>Connection Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Choose between Direct TCP connection or Agent-based monitoring.
            Form will be implemented here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/settings/page.tsx`:
```typescript
export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Settings</h2>
      <p className="text-muted-foreground">General tenant settings will be here.</p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/settings/notifications/page.tsx`:
```typescript
export default function NotificationsSettingsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Notification Settings</h2>
      <p className="text-muted-foreground">
        Configure Slack, Email, and Voice call notification channels here.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/settings/api-keys/page.tsx`:
```typescript
export default function ApiKeysPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">API Keys</h2>
      <p className="text-muted-foreground">
        Generate and manage API keys for agent authentication here.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/settings/escalations/page.tsx`:
```typescript
export default function EscalationsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Escalation Rules</h2>
      <p className="text-muted-foreground">
        Configure when to trigger voice calls based on crash patterns.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/settings/members/page.tsx`:
```typescript
export default function MembersPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Team Members</h2>
      <p className="text-muted-foreground">
        Invite and manage team members for your workspace.
      </p>
    </div>
  );
}
```

`frontend/src/app/(dashboard)/onboarding/page.tsx`:
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OnboardingPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 py-12">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Welcome to DockerSentinel</h1>
        <p className="mt-2 text-muted-foreground">
          Let&apos;s get your container monitoring set up in a few steps.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Step 1: Add a Docker Host</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Onboarding wizard will guide through: name workspace, add first Docker host,
            configure notifications.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 8: Commit**

```bash
cd c:/docker-sentinel
git add frontend/src/app/
git commit -m "feat: add all frontend pages — login, dashboard, hosts, settings, onboarding"
```

---

### Task 19: Final Commit + Verify

- [ ] **Step 1: Add README.md**

Create a brief `README.md` at the project root with setup instructions.

```markdown
# DockerSentinel

Multi-Agent Docker Container Crash Monitor — SaaS Platform

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services
docker compose up -d

# 3. Run database migrations
pip install ".[dev]"
alembic upgrade head

# 4. Seed test data
python scripts/seed_db.py

# 5. Start API server (dev mode)
uvicorn src.api.app:create_app --factory --reload --port 8000

# 6. Start worker (dev mode)
python -m src.worker.main

# 7. Start frontend (dev mode)
cd frontend && npm run dev
```

## Architecture

See `docs/superpowers/specs/2026-04-12-dockersentinel-saas-skeleton-design.md`

## Stack

Python 3.11 | FastAPI | Next.js 15 | Shadcn/ui | LangGraph | PostgreSQL | Redis | Qdrant | Prometheus | Grafana
```

- [ ] **Step 2: Verify project structure**

```bash
cd c:/docker-sentinel
find . -type f | grep -v node_modules | grep -v .git | grep -v __pycache__ | sort
```

Verify all expected files exist.

- [ ] **Step 3: Run linter**

```bash
pip install ruff
ruff check src/ tests/
```

Fix any linting errors.

- [ ] **Step 4: Run tests**

```bash
pip install ".[dev]"
pytest tests/ -v --tb=short
```

Verify tests that can run do run (some will fail due to missing DB — that's expected).

- [ ] **Step 5: Final commit**

```bash
git add README.md
git add -A  # Catch any remaining files
git commit -m "feat: complete DockerSentinel SaaS skeleton — ready for agent implementation"
```
