import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.auth import MeResponse, UserResponse, WsTokenResponse
from src.services import auth_service
from src.services.auth_cookies import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    set_auth_cookies,
)
from src.services.oauth_client import oauth

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OIDC flow — redirects the browser to Google."""
    redirect_uri = f"{settings.api_url}/api/v1/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Google OIDC callback: exchange code → mint JWTs → set cookies → redirect home."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        query = urlencode({"error": str(e)[:100]})
        return RedirectResponse(f"{settings.app_url}/login?{query}")

    userinfo = token.get("userinfo")
    if not userinfo:
        return RedirectResponse(
            f"{settings.app_url}/login?error=no_userinfo"
        )

    user = await auth_service.get_or_create_user_from_oauth(
        db,
        email=userinfo["email"],
        name=userinfo.get("name"),
        avatar_url=userinfo.get("picture"),
        provider="google",
        provider_id=userinfo["sub"],
    )
    await db.commit()

    access = auth_service.create_access_token(user.id, user.tenant_id)
    refresh = auth_service.create_refresh_token(user.id, user.tenant_id)

    resp = RedirectResponse(f"{settings.app_url}/")
    set_auth_cookies(resp, access, refresh)
    return resp


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Rotate both tokens using the refresh_token cookie."""
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from e

    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])
    new_access = auth_service.create_access_token(user_id, tenant_id)
    new_refresh = auth_service.create_refresh_token(user_id, tenant_id)
    set_auth_cookies(response, new_access, new_refresh)
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    """Clear both auth cookies. Idempotent."""
    clear_auth_cookies(response)
    return {"status": "ok"}


@router.post("/ws-token", response_model=WsTokenResponse)
async def get_ws_token(user: User = Depends(get_current_user)) -> WsTokenResponse:
    """Mint a short-lived (60s) WebSocket-only JWT for the authenticated user."""
    token = auth_service.create_ws_token(user.id, user.tenant_id)
    return WsTokenResponse(token=token, expires_in=60)


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile + tenant info."""
    from sqlalchemy import select

    from src.models.tenant import Tenant

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one()

    return MeResponse(
        user=UserResponse.model_validate(user),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
    )
