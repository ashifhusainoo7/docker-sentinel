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
