from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.crash_event import CrashEvent
from src.models.docker_host import DockerHost
from src.models.tenant import Tenant
from src.schemas.dashboard import DashboardMetrics, DashboardSummary, DashboardTimeline

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

_PERIOD_DAYS: dict[str, int] = {"24h": 1, "7d": 7, "30d": 30}
_PERIOD_BUCKET: dict[str, str] = {"24h": "hour", "7d": "day", "30d": "day"}


def _period_window(period: str) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for the given period string."""
    now = datetime.now(timezone.utc)
    days = _PERIOD_DAYS[period]
    return now - timedelta(days=days), now


def _prior_window(period: str) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for the period *before* the given one."""
    now = datetime.now(timezone.utc)
    days = _PERIOD_DAYS[period]
    end = now - timedelta(days=days)
    start = end - timedelta(days=days)
    return start, end


# ---------------------------------------------------------------------------
# Internal data helpers (extracted so tests can patch them easily)
# ---------------------------------------------------------------------------


async def _get_summary_data(tenant: Tenant, db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    # Total crashes in last 24h
    crashes_result = await db.execute(
        select(func.count()).where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= since,
        )
    )
    crashes_24h: int = crashes_result.scalar() or 0

    # Successful restarts in last 24h
    restarts_result = await db.execute(
        select(func.count()).where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= since,
            CrashEvent.restart_attempted.is_(True),
            CrashEvent.restart_success.is_(True),
        )
    )
    restarts_24h: int = restarts_result.scalar() or 0

    # Cache hit rate
    cache_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((CrashEvent.cache_hit.is_(True), 1), else_=0)).label("hits"),
        ).where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= since,
        )
    )
    row = cache_result.one()
    total_events: int = row.total or 0
    cache_hits: int = int(row.hits or 0)
    cache_hit_rate: float = cache_hits / total_events if total_events > 0 else 0.0

    # Active hosts
    hosts_result = await db.execute(
        select(func.count(distinct(DockerHost.id))).where(
            DockerHost.tenant_id == tenant.id,
            DockerHost.status == "connected",
            DockerHost.is_active.is_(True),
        )
    )
    active_hosts: int = hosts_result.scalar() or 0

    return {
        "crashes_24h": crashes_24h,
        "restarts_24h": restarts_24h,
        "cache_hit_rate": round(cache_hit_rate, 4),
        "active_hosts": active_hosts,
    }


async def _get_metrics_data(tenant: Tenant, db: AsyncSession, period: str) -> dict:
    start, end = _period_window(period)
    prior_start, prior_end = _prior_window(period)

    async def _query_mttr(t_start: datetime, t_end: datetime) -> float | None:
        result = await db.execute(
            select(
                func.avg(
                    func.extract("epoch", CrashEvent.resolved_at - CrashEvent.created_at)
                )
            ).where(
                CrashEvent.tenant_id == tenant.id,
                CrashEvent.created_at >= t_start,
                CrashEvent.created_at < t_end,
                CrashEvent.resolved_at.isnot(None),
            )
        )
        val = result.scalar()
        return float(val) if val is not None else None

    async def _query_crash_count(t_start: datetime, t_end: datetime) -> int:
        result = await db.execute(
            select(func.count()).where(
                CrashEvent.tenant_id == tenant.id,
                CrashEvent.created_at >= t_start,
                CrashEvent.created_at < t_end,
            )
        )
        return result.scalar() or 0

    current_mttr = await _query_mttr(start, end)
    prior_mttr = await _query_mttr(prior_start, prior_end)
    crashes_total = await _query_crash_count(start, end)
    prior_crashes = await _query_crash_count(prior_start, prior_end)

    # Delta calculations — null when prior period has no data
    def _delta_pct(current: float | None, prior: float | None) -> float | None:
        if current is None or prior is None or prior == 0:
            return None
        return round((current - prior) / prior * 100, 1)

    mttr_delta_pct = _delta_pct(current_mttr, prior_mttr)
    crashes_delta_pct = _delta_pct(float(crashes_total), float(prior_crashes))

    # Severity breakdown
    sev_result = await db.execute(
        select(CrashEvent.severity, func.count().label("cnt"))
        .where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= start,
            CrashEvent.created_at < end,
            CrashEvent.severity.isnot(None),
        )
        .group_by(CrashEvent.severity)
    )
    severity_breakdown: dict[str, int] = {row.severity: row.cnt for row in sev_result}

    # Category breakdown
    cat_result = await db.execute(
        select(CrashEvent.category, func.count().label("cnt"))
        .where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= start,
            CrashEvent.created_at < end,
            CrashEvent.category.isnot(None),
        )
        .group_by(CrashEvent.category)
    )
    category_breakdown: dict[str, int] = {row.category: row.cnt for row in cat_result}

    return {
        "period": period,
        "mttr_seconds": round(current_mttr, 2) if current_mttr is not None else None,
        "mttr_delta_pct": mttr_delta_pct,
        "crashes_total": crashes_total,
        "crashes_delta_pct": crashes_delta_pct,
        "severity_breakdown": severity_breakdown,
        "category_breakdown": category_breakdown,
    }


async def _get_timeline_data(tenant: Tenant, db: AsyncSession, period: str) -> dict:
    start, end = _period_window(period)
    bucket_type = _PERIOD_BUCKET[period]  # "hour" or "day"
    days = _PERIOD_DAYS[period]

    # Build expected bucket list (Python-side gap fill)
    if bucket_type == "hour":
        # 24 hourly buckets; floor to hour
        buckets = [
            (end - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
            for i in range(days * 24 - 1, -1, -1)
        ]
    else:
        # N daily buckets; floor to day
        buckets = [
            (end - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            for i in range(days - 1, -1, -1)
        ]

    # Query DB for actual counts grouped by bucket
    trunc_fn = func.date_trunc(bucket_type, CrashEvent.created_at)
    crash_result = await db.execute(
        select(trunc_fn.label("bucket"), func.count().label("cnt"))
        .where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= start,
            CrashEvent.created_at < end,
        )
        .group_by("bucket")
        .order_by("bucket")
    )
    crash_map: dict[datetime, int] = {}
    for row in crash_result:
        key = row.bucket
        if key.tzinfo is None:
            key = key.replace(tzinfo=timezone.utc)
        crash_map[key] = row.cnt

    restart_result = await db.execute(
        select(trunc_fn.label("bucket"), func.count().label("cnt"))
        .where(
            CrashEvent.tenant_id == tenant.id,
            CrashEvent.created_at >= start,
            CrashEvent.created_at < end,
            CrashEvent.restart_attempted.is_(True),
            CrashEvent.restart_success.is_(True),
        )
        .group_by("bucket")
        .order_by("bucket")
    )
    restart_map: dict[datetime, int] = {}
    for row in restart_result:
        key = row.bucket
        if key.tzinfo is None:
            key = key.replace(tzinfo=timezone.utc)
        restart_map[key] = row.cnt

    # Gap-fill: every bucket gets a point even if not in DB result
    points = []
    for bucket_dt in buckets:
        # Normalise to UTC-aware for lookup
        if bucket_dt.tzinfo is None:
            bucket_dt = bucket_dt.replace(tzinfo=timezone.utc)
        points.append(
            {
                "t": bucket_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "crashes": crash_map.get(bucket_dt, 0),
                "restarts": restart_map.get(bucket_dt, 0),
            }
        )

    return {"period": period, "bucket": bucket_type, "points": points}


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard summary: crash/restart counts, cache hit rate, active hosts."""
    data = await _get_summary_data(tenant, db)
    return DashboardSummary(**data)


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
    period: str = Query("24h", pattern="^(24h|7d|30d)$"),
):
    """Key operational metrics with period-over-period deltas."""
    data = await _get_metrics_data(tenant, db, period)
    return DashboardMetrics(**data)


@router.get("/timeline", response_model=DashboardTimeline)
async def get_timeline(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
    period: str = Query("24h", pattern="^(24h|7d|30d)$"),
):
    """Crash/restart time series for charting, with zero-padded gap-fill."""
    data = await _get_timeline_data(tenant, db, period)
    return DashboardTimeline(**data)
