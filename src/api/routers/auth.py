from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.auth import MeResponse, Token, TokenRefresh, UserResponse
from src.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/github")
async def github_login():
    """Initiate GitHub OAuth flow — returns redirect URL."""
    raise NotImplementedError(
        "GitHub OAuth not yet implemented. "
        "Will use authlib to redirect to GitHub authorization URL."
    )


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle GitHub OAuth callback — exchange code for tokens."""
    raise NotImplementedError(
        "GitHub OAuth callback not yet implemented. "
        "Will exchange code for access token, fetch user profile, "
        "call get_or_create_user_from_oauth, return JWT tokens."
    )


@router.get("/google")
async def google_login():
    """Initiate Google OAuth flow — returns redirect URL."""
    raise NotImplementedError(
        "Google OAuth not yet implemented. "
        "Will use authlib to redirect to Google authorization URL."
    )


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback — exchange code for tokens."""
    raise NotImplementedError(
        "Google OAuth callback not yet implemented. "
        "Will exchange code for access token, fetch user profile, "
        "call get_or_create_user_from_oauth, return JWT tokens."
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(body: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh an expired access token."""
    try:
        payload = auth_service.decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from e

    import uuid
    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])

    return Token(
        access_token=auth_service.create_access_token(user_id, tenant_id),
        refresh_token=auth_service.create_refresh_token(user_id, tenant_id),
    )


@router.post("/logout")
async def logout():
    """Logout — client should discard tokens."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from src.models.tenant import Tenant

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one()

    return MeResponse(
        user=UserResponse.model_validate(user),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
    )
