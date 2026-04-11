import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, get_tenant
from src.models.tenant import Tenant
from src.models.user import User
from src.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from src.services import api_key_service

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await api_key_service.list_api_keys(db, tenant.id)


@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    data: ApiKeyCreate,
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    api_key, full_key = await api_key_service.create_api_key(
        db, tenant.id, user.id, data
    )
    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key=full_key,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    revoked = await api_key_service.revoke_api_key(db, tenant.id, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
