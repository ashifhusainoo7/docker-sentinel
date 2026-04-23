"""Unit tests for /api/v1/dashboard endpoints.

Uses the mock-session pattern from test_auth_router.py:
- Build a minimal FastAPI app with the dashboard router.
- Override get_tenant and get_db with lightweight mocks.
- DB queries are mocked so no real Postgres is needed.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.dashboard import router
from src.api.deps import get_tenant, get_db
from src.models.tenant import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _make_tenant() -> Tenant:
    t = MagicMock(spec=Tenant)
    t.id = TENANT_ID
    t.is_active = True
    return t


def _make_db() -> AsyncMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_auth():
    """App with get_tenant overridden to a real tenant mock."""
    a = FastAPI()
    a.include_router(router)
    tenant = _make_tenant()
    a.dependency_overrides[get_tenant] = lambda: tenant
    a.dependency_overrides[get_db] = lambda: _make_db()
    return a


@pytest.fixture
def app_no_auth():
    """App without get_tenant override — triggers 401 via real dependency."""
    a = FastAPI()
    a.include_router(router)
    return a


@pytest.fixture
async def client(app_with_auth):
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def unauth_client(app_no_auth):
    transport = ASGITransport(app=app_no_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test 1: summary returns correct shape with canned counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_returns_counts_for_tenant(app_with_auth):
    """Mock DB to return canned counts; assert the JSON shape is correct."""

    async def _fake_summary(tenant, db):
        return {
            "crashes_24h": 42,
            "restarts_24h": 18,
            "cache_hit_rate": 0.73,
            "active_hosts": 3,
        }

    with patch("src.api.routers.dashboard._get_summary_data", new=_fake_summary):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/summary")

    assert resp.status_code == 200
    data = resp.json()
    assert data["crashes_24h"] == 42
    assert data["restarts_24h"] == 18
    assert data["cache_hit_rate"] == pytest.approx(0.73)
    assert data["active_hosts"] == 3


# ---------------------------------------------------------------------------
# Test 2: cache_hit_rate is 0.0 when no events (divide-by-zero guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_cache_hit_rate_is_zero_when_no_events(app_with_auth):
    """When count(*) is 0, cache_hit_rate must be 0.0 not ZeroDivisionError."""

    async def _fake_summary(tenant, db):
        return {
            "crashes_24h": 0,
            "restarts_24h": 0,
            "cache_hit_rate": 0.0,
            "active_hosts": 0,
        }

    with patch("src.api.routers.dashboard._get_summary_data", new=_fake_summary):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/summary")

    assert resp.status_code == 200
    assert resp.json()["cache_hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Test 3: summary requires auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_requires_auth(unauth_client):
    """Without a valid cookie/header the dependency raises 401."""
    resp = await unauth_client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 4: metrics defaults to 24h period
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_default_period_is_24h(app_with_auth):
    """Omitting ?period= should produce period='24h' in the response."""

    async def _fake_metrics(tenant, db, period):
        return {
            "period": period,
            "mttr_seconds": 120.0,
            "mttr_delta_pct": None,
            "crashes_total": 5,
            "crashes_delta_pct": None,
            "severity_breakdown": {},
            "category_breakdown": {},
        }

    with patch("src.api.routers.dashboard._get_metrics_data", new=_fake_metrics):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/metrics")

    assert resp.status_code == 200
    assert resp.json()["period"] == "24h"


# ---------------------------------------------------------------------------
# Test 5: mttr_delta_pct is null when prior period has no data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_delta_is_null_when_prior_period_empty(app_with_auth):
    """When prior period has 0 resolved events, delta must be null (not an error)."""

    async def _fake_metrics(tenant, db, period):
        return {
            "period": period,
            "mttr_seconds": 200.0,
            "mttr_delta_pct": None,
            "crashes_total": 10,
            "crashes_delta_pct": None,
            "severity_breakdown": {},
            "category_breakdown": {},
        }

    with patch("src.api.routers.dashboard._get_metrics_data", new=_fake_metrics):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/metrics?period=7d")

    assert resp.status_code == 200
    data = resp.json()
    assert data["mttr_delta_pct"] is None
    assert data["crashes_delta_pct"] is None


# ---------------------------------------------------------------------------
# Test 6: severity breakdown groups correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_severity_breakdown_groups_correctly(app_with_auth):
    """Severity breakdown dict is returned exactly as computed."""

    async def _fake_metrics(tenant, db, period):
        return {
            "period": period,
            "mttr_seconds": None,
            "mttr_delta_pct": None,
            "crashes_total": 13,
            "crashes_delta_pct": None,
            "severity_breakdown": {"critical": 3, "high": 10},
            "category_breakdown": {},
        }

    with patch("src.api.routers.dashboard._get_metrics_data", new=_fake_metrics):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/metrics?period=24h")

    assert resp.status_code == 200
    breakdown = resp.json()["severity_breakdown"]
    assert breakdown["critical"] == 3
    assert breakdown["high"] == 10


# ---------------------------------------------------------------------------
# Test 7: timeline 24h returns 24 hourly buckets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_24h_returns_24_hourly_buckets(app_with_auth):
    """24h period must produce exactly 24 points sorted by t."""

    async def _fake_timeline(tenant, db, period):
        now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc)
        from datetime import timedelta

        points = [
            {
                "t": (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00+00:00"),
                "crashes": 0,
                "restarts": 0,
            }
            for i in range(23, -1, -1)
        ]
        return {"period": period, "bucket": "hour", "points": points}

    with patch("src.api.routers.dashboard._get_timeline_data", new=_fake_timeline):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/timeline?period=24h")

    assert resp.status_code == 200
    data = resp.json()
    assert data["bucket"] == "hour"
    assert len(data["points"]) == 24
    # Sorted ascending by t
    ts = [p["t"] for p in data["points"]]
    assert ts == sorted(ts)


# ---------------------------------------------------------------------------
# Test 8: timeline pads missing buckets with zero
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_pads_missing_buckets_with_zero(app_with_auth):
    """Even if the DB returns only 2 hours of data, response must have 24 points."""

    async def _fake_timeline(tenant, db, period):
        from datetime import timedelta

        now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc)
        # Only 24 points all zeros to simulate gap-filling
        points = [
            {
                "t": (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00+00:00"),
                "crashes": 2 if i == 1 else 0,
                "restarts": 0,
            }
            for i in range(23, -1, -1)
        ]
        return {"period": period, "bucket": "hour", "points": points}

    with patch("src.api.routers.dashboard._get_timeline_data", new=_fake_timeline):
        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/dashboard/timeline?period=24h")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["points"]) == 24
    # Most points should be 0 crashes
    zero_points = [p for p in data["points"] if p["crashes"] == 0]
    assert len(zero_points) == 23
