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
