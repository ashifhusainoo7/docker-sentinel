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
