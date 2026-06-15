# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-15

Initial alpha release. Core crash → analyze → notify → persist flow works end-to-end.

### Added

- Docker crash detection for `die` / `oom` / `kill` events over TCP or the local named pipe.
- Event filtering and per-container dedup (60s window).
- Per-tenant crash streams published to Redis.
- LangGraph orchestration: analyze → optional restart → notify → persist `CrashEvent`.
- LLM root-cause analysis via OpenAI `gpt-4o-mini` with `gpt-4o` fallback, structured into a `CrashAnalysis` model.
- Qdrant semantic cache (fastembed `bge-small-en-v1.5`, 384-dim cosine) with per-tenant isolation; repeat crashes skip the LLM.
- Slack (Block Kit) and HTML email (Gmail SMTP via `aiosmtplib`) notifications.
- Per-tenant `NotificationConfig` with an `is_enabled` mute switch.
- FastAPI API server (auth, CRUD, dashboard endpoints, WebSocket live feed) and a separate worker process.
- Docker Compose stack: PostgreSQL 16, Redis 7, Qdrant, Prometheus, Grafana.
- Next.js 15 + Shadcn/ui dashboard (in progress).
- MIT license, GitHub Sponsors `FUNDING.yml`, CI matrix (Python 3.11/3.12 + Docker build), README badges.

### Fixed

- Crash-safe, reconnect-resilient Redis crash-event consumer (consume/ack/reclaim).
- Hardened listener thread-to-asyncio bridge against backpressure and stale clients.
- Retry on crash-event persist so a transient DB error doesn't orphan the row.
- Isolated per-host listener startup so one bad host can't disable all monitoring.

### Known limitations

- Customer-hosted agent container (`src.agent_container.main`) is a skeleton, not wired end-to-end.
- Frontend dashboard is partially scaffolded and not yet bound to live workflow data.
- No published Docker images yet — build from source via Compose.

[Unreleased]: https://github.com/ashifhusainoo7/docker-sentinel/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ashifhusainoo7/docker-sentinel/releases/tag/v0.1.0
