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
