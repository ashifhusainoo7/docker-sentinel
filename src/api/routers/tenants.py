from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, get_tenant
from src.models.tenant import Tenant
from src.models.user import User
from src.schemas.tenant import (
    InviteMember,
    MemberResponse,
    TenantResponse,
    TenantUpdate,
)
from src.services import tenant_service

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(tenant: Tenant = Depends(get_tenant)):
    return tenant


@router.patch("/current", response_model=TenantResponse)
async def update_current_tenant(
    data: TenantUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    updated = await tenant_service.update_tenant(db, tenant.id, data.name)
    return updated


@router.get("/current/members", response_model=list[MemberResponse])
async def list_members(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await tenant_service.list_members(db, tenant.id)


@router.post("/current/members/invite")
async def invite_member(
    data: InviteMember,
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    raise NotImplementedError(
        "Member invitation not yet implemented. "
        "Will send email invitation and create pending user record."
    )
