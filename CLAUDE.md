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
