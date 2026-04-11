import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.models.tenant import Tenant
from src.models.user import User


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


async def get_or_create_user_from_oauth(
    db: AsyncSession,
    email: str,
    name: str | None,
    avatar_url: str | None,
    provider: str,
    provider_id: str,
) -> User:
    """Find existing user by email or create new user + tenant on first login."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        return user

    # Create new tenant for first-time user
    slug = email.split("@")[0].lower().replace(".", "-")
    tenant = Tenant(name=f"{name or slug}'s Workspace", slug=f"{slug}-{uuid.uuid4().hex[:6]}")
    db.add(tenant)
    await db.flush()

    # Create user as owner
    user = User(
        tenant_id=tenant.id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=provider,
        oauth_provider_id=provider_id,
        role="owner",
    )
    db.add(user)
    await db.flush()
    return user
