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
