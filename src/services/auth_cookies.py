from fastapi import Response

from config.settings import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/v1/auth"


def _secure() -> bool:
    return settings.environment != "development"


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    """Set both auth cookies with production-safe flags.

    The access_token cookie is scoped to `/` so every API request carries it.
    The refresh_token cookie is scoped to `/api/v1/auth` so non-auth endpoints
    never see it in the request — narrower exposure surface.
    """
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,
        secure=_secure(),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        httponly=True,
        secure=_secure(),
        samesite="lax",
        path=REFRESH_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    """Delete both auth cookies by setting Max-Age=0 on their scoped paths."""
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
