# Contributing to DockerSentinel

Thanks for your interest in contributing! DockerSentinel is in early alpha, so
issues, ideas, and pull requests are all welcome.

## Ways to contribute

- **Report a bug** — open an issue with steps to reproduce, expected vs. actual behavior, and logs if you have them.
- **Suggest a feature** — open an issue describing the use case before writing code, so we can align on the approach.
- **Send a pull request** — for anything beyond a trivial fix, please open an issue first.

## Development setup

Requires **Python 3.12**, **Docker Desktop**, and (optionally) **Node.js 18+** for the frontend.

```bash
git clone https://github.com/ashifhusainoo7/docker-sentinel.git
cd docker-sentinel

py -3.12 -m pip install -e ".[dev]"     # Python deps
cd frontend && npm install && cd ..      # frontend deps (optional)

cp .env.example .env                      # fill in values (see README)
docker compose up -d postgres redis qdrant
py -3.12 -m alembic upgrade head
```

See the [README](README.md) for the full end-to-end demo.

## Before you open a PR

Run the checks locally — CI runs the same on Python 3.11 and 3.12:

```bash
ruff check .                                                              # lint (line length 100)
ruff format .                                                            # format
py -3.12 -m pytest tests/unit/ tests/test_services/test_crash_event_schema.py -v   # tests
```

Unit tests must not call OpenAI, Slack, SMTP, Qdrant, or Docker — mock all external integrations.

## Conventions

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- **Types:** type hints on all function signatures.
- **Async:** SQLAlchemy async sessions, async FastAPI endpoints, asyncio worker.
- **Layering:** routers → services → models; routers never touch the DB directly.
- **Multi-tenant:** every table has `tenant_id`, filtered at the service layer.
- **Changelog:** add a line under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md) for user-facing changes.

## Pull request flow

1. Branch off `master` (e.g. `feat/short-description`).
2. Make your change with tests.
3. Ensure lint + tests pass.
4. Open a PR into `master` with a clear description of what and why.

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
