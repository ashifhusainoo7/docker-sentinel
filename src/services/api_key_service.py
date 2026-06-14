import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import ApiKey
from src.schemas.api_key import ApiKeyCreate


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, key_hash, key_prefix)."""
    key = f"dsk_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()
    key_prefix = key[:12]
    return key, key_hash, key_prefix


def verify_api_key(key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(key.encode(), key_hash.encode())


async def create_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, data: ApiKeyCreate
) -> tuple[ApiKey, str]:
    """Returns (api_key_model, full_key). Full key is only available at creation."""
    key, key_hash, key_prefix = generate_api_key()
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=data.expires_in_days)

    api_key = ApiKey(
        tenant_id=tenant_id,
        created_by=user_id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=data.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()
    return api_key, key


async def list_api_keys(db: AsyncSession, tenant_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.tenant_id == tenant_id, ApiKey.is_active)
    )
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, key_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return False
    api_key.is_active = False
    await db.flush()
    return True


async def validate_api_key(db: AsyncSession, key: str) -> ApiKey | None:
    """Validate an API key and return the associated ApiKey model."""
    prefix = key[:12]
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active)
    )
    for api_key in result.scalars().all():
        if verify_api_key(key, api_key.key_hash):
            now = datetime.now(UTC)
            if api_key.expires_at and api_key.expires_at < now:
                return None
            api_key.last_used_at = now
            await db.flush()
            return api_key
    return None
