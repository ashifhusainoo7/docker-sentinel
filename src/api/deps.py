import uuid
from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tenant import Tenant
from src.models.user import User
from src.services import auth_service
from src.services.auth_cookies import ACCESS_COOKIE
from src.services.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    """Resolve the current user from the access_token cookie or Bearer header.

    Cookie is preferred; header is a fallback for programmatic/API-key use.
    """
    token = request.cookies.get(ACCESS_COOKIE)
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant inactive")
    return tenant
