# Google OAuth (Phase 4) — Design

**Date:** 2026-04-23
**Scope:** Phase 4 item #17 from `work-tracking/PROGRESS.md` — replace the `NotImplementedError` Google OAuth stubs with a production-grade OIDC login flow. Drops the parallel GitHub stubs entirely.

Out of scope:
- GitHub OAuth (removed, not deferred — can be re-added later using the same pattern).
- Refresh-token blacklist / theft-detection / logout-everywhere.
- Email whitelist (auto-provision tenants for any Google account).
- Frontend test harness (no Jest/Vitest configured; manual smoke test covers the UI).
- PKCE (confidential client with server-side secret makes it belt-and-suspenders).
- Prometheus auth metrics.

## Goals

1. Clicking "Continue with Google" on `/login` redirects through Google's OIDC consent flow and returns the user to the app homepage authenticated.
2. Tokens are delivered via HTTP-only cookies — JavaScript never touches them. XSS cannot steal them.
3. Tokens auto-refresh on expiry without disturbing the user experience.
4. First sign-in auto-provisions a `Tenant` and `User` pair; subsequent logins reuse them.
5. CSRF, ID token signature verification, and state validation are handled by Authlib (no hand-rolled crypto).
6. CORS is tightened so credentialed requests only flow between the configured frontend and backend origins.
7. GitHub buttons and routes are removed everywhere.

## Non-goals

- Production deployment with HTTPS, real domain, and published OAuth consent screen (we document the dev flow; prod is a later concern).
- Token revocation endpoints.
- Multi-factor authentication at the app layer (Google handles this upstream).
- SSO or SAML.

## Architecture

```
┌──────────────────┐        ┌─────────────────┐        ┌──────────────────┐
│  Frontend        │        │  Backend (API)  │        │  Google OAuth    │
│  localhost:3000  │        │  localhost:8000 │        │  accounts.google │
└──────────────────┘        └─────────────────┘        └──────────────────┘
         │                           │                           │
  1. Click "Continue with Google"    │                           │
         │  GET /api/v1/auth/google  │                           │
         │──────────────────────────▶│                           │
         │                           │  Authlib mints state+     │
         │                           │  nonce, stores in          │
         │                           │  SessionMiddleware cookie  │
         │                           │                            │
         │◀──302 Redirect────────────│                           │
         │  to Google with            │                           │
         │  state, nonce, scope=      │                           │
         │  "openid email profile"    │                           │
         │                           │                           │
  2. User authorizes on Google       │                           │
         │                           │                           │
         │─────GET /api/v1/auth/google/callback?code=...&state=───▶
         │                           │                           │
         │                           │ 3. Authlib verifies state │
         │                           │    + exchanges code for    │
         │                           │    id_token + userinfo ───▶│
         │                           │                            │
         │                           │◀──ID token (JWT signed by ─│
         │                           │   Google's JWKs) + userinfo│
         │                           │                            │
         │                           │ 4. get_or_create_user      │
         │                           │    → Tenant + User on      │
         │                           │    first sign-in           │
         │                           │                            │
         │                           │ 5. Mint access (30m)       │
         │                           │    + refresh (7d) JWTs     │
         │                           │                            │
         │◀──302 Redirect to / ───────│                           │
         │   + Set-Cookie:            │                           │
         │     access_token (HttpOnly,│                           │
         │     Path=/, 30m TTL)       │                           │
         │   + Set-Cookie:            │                           │
         │     refresh_token (HttpOnly,│                          │
         │     Path=/api/v1/auth,     │                           │
         │     7d TTL)                │                           │
         │                           │                           │
  6. Frontend lands at "/",         │                            │
     calls GET /api/v1/auth/me       │                           │
     (browser auto-sends cookies)   │                           │
         │──────────────────────────▶│                           │
         │◀──200 JSON user info──────│                           │
         │                           │                           │
  7. Every API call auto-sends       │                           │
     cookies. 401 → frontend hits    │                           │
     /refresh, backend rotates       │                           │
     both tokens.                    │                           │
```

## Key design decisions

### HTTP-only cookies, not URL params or localStorage

`access_token` and `refresh_token` are set as `HttpOnly; SameSite=Lax; Path=<scoped>`. JavaScript has no way to read or write them. Cross-site requests can't send them. Access token scoped to `/`; refresh token scoped to `/api/v1/auth` so it's never sent to any other endpoint.

**Why:** 2026 production baseline. localStorage exposes tokens to any XSS vulnerability; URL params leak them to browser history and server logs.

### Authlib + OIDC discovery URL

`oauth.register("google", server_metadata_url=".../.well-known/openid-configuration")` → Authlib pulls Google's discovery doc once, gets `authorization_endpoint`, `token_endpoint`, `jwks_uri`. Automatic signature verification on the `id_token` against Google's rotated JWKs.

**Why:** Discovery URL means we never hard-code endpoint paths. ID token verification is done correctly (audience check, signature check, issuer check) without us writing crypto.

### SessionMiddleware for state + nonce

Starlette's `SessionMiddleware` signs a server-side-generated session cookie with `settings.jwt_secret_key`. Authlib stashes `state` and `nonce` there between the `/google` redirect and the `/google/callback` return. On callback, Authlib validates both — mismatched state raises, protecting against CSRF-style OAuth attacks.

**Why:** Standard Starlette integration pattern. No hand-rolled CSRF nonce storage.

### Refresh-token rotation on every /refresh

Each `POST /api/v1/auth/refresh` issues a brand-new access + refresh cookie. The old refresh JWT is left to expire naturally (no blacklist — acceptable at portfolio scale).

**Why:** Rotation limits the window in which a stolen refresh token is useful. Blacklisting is a future hardening step (documented as deferred).

### CORS tightened for credentials

`allow_origins=[settings.app_url]` (not `*`), `allow_credentials=True`. Cookies only flow from the configured frontend origin.

**Why:** Required — browsers reject credentialed requests with wildcard origins. Also a security boundary: no random page can hit our API with the user's cookies.

### Auto-provision tenant on first sign-in

`get_or_create_user_from_oauth` (already implemented) creates a `Tenant(name="<name>'s Workspace", slug="<email-prefix>-<uuid>")` and `User(role="owner", oauth_provider="google")` when an email isn't found. No admin approval step.

**Why:** Self-serve portfolio demo. Anyone with a Google account becomes an owner of their own tenant. Whitelist check (allowed emails only) is a 5-line add for later if needed.

### `Secure` flag only in production

`Secure` requires HTTPS. Setting it in dev (http://localhost) would make the browser reject the cookie entirely. Flag is driven by `settings.environment != "development"`.

### GitHub removal, not deferral

Both `/api/v1/auth/github` and `/api/v1/auth/github/callback` routes are deleted. The frontend's GitHub button is deleted. `.env.example` keeps `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` placeholders in case someone wants to add the mirror pattern later.

**Why:** A broken GitHub button is a demo wart. Re-adding it when needed is a 20-line copy of the Google router.

## Component specifications

### New file: `src/services/oauth_client.py`

Module-level Authlib `OAuth` registry.

```python
from authlib.integrations.starlette_client import OAuth

from config.settings import settings

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

### New file: `src/services/auth_cookies.py`

Centralized cookie names + lifetimes + flags.

```python
from fastapi import Response

from config.settings import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/v1/auth"


def _secure() -> bool:
    return settings.environment != "development"


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
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
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
```

### Modified: `src/api/deps.py`

`get_current_user` reads cookie first, falls back to `Authorization: Bearer <token>` for programmatic access.

```python
from fastapi import Depends, Header, HTTPException, Request
import jwt

from src.services import auth_service
from src.services.auth_cookies import ACCESS_COOKIE


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired") from None
    except Exception as e:
        raise HTTPException(401, "Invalid token") from e

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "User not found")
    return user
```

### Modified: `src/api/app.py`

Add `SessionMiddleware`; tighten CORS.

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key,
    same_site="lax",
    https_only=settings.environment != "development",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Modified: `src/api/routers/auth.py`

Delete GitHub routes. Rewrite Google routes to real implementations. Rewrite `/refresh` and `/logout` to use cookies.

```python
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.auth import MeResponse, UserResponse
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
    redirect_uri = f"{settings.api_url}/api/v1/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        return RedirectResponse(
            f"{settings.app_url}/login?"
            + urlencode({"error": str(e)[:100]})
        )

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
async def refresh(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
    except Exception as e:
        raise HTTPException(401, "Invalid refresh token") from e

    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])
    new_access = auth_service.create_access_token(user_id, tenant_id)
    new_refresh = auth_service.create_refresh_token(user_id, tenant_id)
    set_auth_cookies(response, new_access, new_refresh)
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    from src.models.tenant import Tenant

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one()
    return MeResponse(
        user=UserResponse.model_validate(user),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
    )
```

`TokenRefresh` schema import removed (no longer takes a body). GitHub routes deleted.

### Modified: `src/schemas/auth.py`

Delete `TokenRefresh` and `Token` from the file if nothing else uses them (check before removing). `MeResponse`, `UserResponse` stay.

### Modified: `frontend/src/app/(auth)/login/page.tsx`

Drop GitHub button, add Google "G" logo to the remaining button.

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function GoogleLogo() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.08H42V20H24v8h11.3c-1.65 4.66-6.08 8-11.3 8-6.63 0-12-5.37-12-12s5.37-12 12-12c3.06 0 5.85 1.15 7.96 3.04l5.66-5.66C34.05 6.05 29.27 4 24 4 12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20c0-1.34-.14-2.65-.4-3.92z"/>
      <path fill="#FF3D00" d="M6.31 14.69l6.57 4.82C14.66 15.05 18.96 12 24 12c3.06 0 5.85 1.15 7.96 3.04l5.66-5.66C34.05 6.05 29.27 4 24 4 16.32 4 9.66 8.34 6.31 14.69z"/>
      <path fill="#4CAF50" d="M24 44c5.17 0 9.86-1.98 13.41-5.2l-6.19-5.24C29.14 34.82 26.72 36 24 36c-5.2 0-9.62-3.32-11.28-7.95l-6.53 5.03C9.49 39.56 16.23 44 24 44z"/>
      <path fill="#1976D2" d="M43.6 20.08H42V20H24v8h11.3c-.79 2.24-2.24 4.17-4.08 5.57l.01-.01 6.19 5.24C37.0 38.53 44 33 44 24c0-1.34-.14-2.65-.4-3.92z"/>
    </svg>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">DockerSentinel</CardTitle>
          <CardDescription>Multi-Agent Docker Container Crash Monitor</CardDescription>
        </CardHeader>
        <CardContent>
          <a href={`${API_URL}/api/v1/auth/google`}>
            <Button className="w-full gap-2" variant="outline">
              <GoogleLogo />
              Continue with Google
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Modified: `frontend/src/app/(auth)/callback/page.tsx`

The backend callback redirects directly to `/`, so this page is no longer on the happy path. Simplify it to a safety-net redirect:

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CallbackPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/"); }, [router]);
  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing in...</p>
    </div>
  );
}
```

### Modified: `frontend/src/lib/auth.ts`

Remove `setTokens` / `getTokens` / localStorage helpers. Expose `getMe()` and `logout()` that talk to the backend over cookies.

```ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getMe() {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function logout() {
  await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
```

### Modified: `frontend/src/lib/api.ts`

Central fetch wrapper:
- Every call uses `credentials: "include"`.
- On 401 from a non-auth endpoint, call `/api/v1/auth/refresh` once; if that succeeds, retry the original request; otherwise redirect to `/login`.
- No token-reading logic (browser handles cookies).

### Modified: `frontend/src/hooks/use-auth.ts`

Remove token-reading logic; call `getMe()` on mount, expose `user` + `logout()`.

## Error handling

| Failure | Where | Response |
|---|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` empty | `oauth.google.authorize_redirect` | Authlib raises. 500 to caller. Operator populates `.env`. |
| User denies consent | `/google/callback` | Authlib raises in `authorize_access_token`. Redirect to `/login?error=...`. |
| State mismatch (CSRF) | `authorize_access_token` | `MismatchingStateError`. Redirect to `/login?error=...`. |
| ID token signature invalid / `aud` wrong | Authlib JWT verification | Raises. Redirect to `/login?error=...`. |
| `userinfo` missing from token | callback body | Redirect to `/login?error=no_userinfo`. |
| DB failure during user creation | `db.commit()` | Unhandled → 500. Acceptable at portfolio scale. |
| Cookie rejected by browser | Usually misconfigured SameSite / Secure | User lands at `/`, `get_me` returns 401, frontend redirects to `/login`. |
| Access token expired | any subsequent API call | 401 → frontend calls `/refresh` → success retries original request; failure redirects to `/login`. |
| Refresh token expired | `/refresh` | 401 → frontend redirects to `/login`. |

## Configuration

### New settings — none

All settings already present:
- `google_client_id`, `google_client_secret` — populated from `.env`.
- `jwt_secret_key` — reused for SessionMiddleware signing.
- `app_url` (`http://localhost:3000`) — frontend redirect target.
- `api_url` (`http://localhost:8000`) — used for `redirect_uri` sent to Google.
- `environment` — drives `Secure` cookie + SessionMiddleware `https_only` flags.

### Environment additions

Add to `.env` before running:
```
GOOGLE_CLIENT_ID=<from Google Console>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<from Google Console>
```

### Google Cloud Console (one-time user action)

1. https://console.cloud.google.com/ → create project.
2. APIs & Services → OAuth consent screen → External → fill in app name, support email, scopes (`openid`, `email`, `profile`), add own Gmail to test users.
3. APIs & Services → Credentials → Create OAuth client ID → Web application → authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`.
4. Copy Client ID + Client Secret into `.env`.

## Dependencies

Already in `pyproject.toml`:
- `authlib>=1.3.0`
- `httpx>=0.27.0`
- `pyjwt[crypto]>=2.8.0`

To verify / add:
- `itsdangerous>=2.0.0` — required by Starlette's `SessionMiddleware`. If not explicit, add to the dependencies list.

## Testing

### Unit tests (backend)

**`tests/unit/api/test_auth_cookies.py`** (4 tests):
- `test_set_auth_cookies_writes_access_and_refresh` — names, flags, paths, max-age.
- `test_set_auth_cookies_secure_in_production` — `Secure` flag on.
- `test_set_auth_cookies_insecure_in_development` — no `Secure`.
- `test_clear_auth_cookies_deletes_both` — `Max-Age=0` on both.

**`tests/unit/api/test_auth_router.py`** (9 tests, Authlib mocked):
- `test_google_login_redirects_to_google`
- `test_google_callback_sets_cookies_and_redirects_to_app_url`
- `test_google_callback_creates_user_on_first_login`
- `test_google_callback_returns_existing_user_on_second_login`
- `test_google_callback_redirects_to_login_on_state_mismatch`
- `test_google_callback_redirects_to_login_when_userinfo_missing`
- `test_refresh_rotates_both_cookies_on_valid_refresh_token`
- `test_refresh_returns_401_when_no_cookie`
- `test_logout_clears_both_cookies`

**`tests/unit/api/test_deps_auth.py`** (5 tests):
- `test_get_current_user_reads_cookie`
- `test_get_current_user_falls_back_to_authorization_header`
- `test_get_current_user_prefers_cookie_over_header`
- `test_get_current_user_401_when_no_token`
- `test_get_current_user_401_when_token_expired`

**`tests/unit/services/test_oauth_client.py`** (2 tests):
- `test_oauth_client_registers_google_with_correct_scope`
- `test_oauth_client_uses_google_discovery_url`

### Existing test updates

`tests/test_api/test_auth.py` likely asserts the `NotImplementedError` stub behavior. Rewrite or replace at implementation time.

### No real Google OAuth tests in CI

All Authlib calls mocked. CI never reaches Google.

### Expected counts

- +4 cookie helper tests
- +9 router tests (replacing ~4 stub tests — net +5)
- +5 dep resolution tests
- +2 OAuth client shape tests
- = ~16 net new tests

Current: 109 tests. After: ~125.

### Manual smoke test

1. Complete Google Console setup (Client ID + Secret → `.env`).
2. `docker compose up -d postgres redis`.
3. `py -3.12 -m alembic upgrade head`.
4. `py -3.12 -m uvicorn src.api.app:create_app --factory --reload --port 8000`.
5. `cd frontend && npm run dev`.
6. Open `http://localhost:3000/login` — button shows Google "G" logo.
7. Click → Google consent screen → authorize with test-user Gmail.
8. Redirected to `http://localhost:3000/`. DevTools → Application → Cookies: `access_token` + `refresh_token`, both `HttpOnly`, `SameSite=Lax`, no `Secure` in dev.
9. Dashboard loads, calls `GET /api/v1/auth/me` via cookies, renders user info.
10. Query DB:
    ```bash
    docker compose exec -T postgres psql -U sentinel -d sentinel -c \
      "SELECT u.email, u.name, u.oauth_provider, u.role, t.name AS tenant FROM users u JOIN tenants t ON u.tenant_id = t.id;"
    ```
    Expected: one row, `oauth_provider='google'`, `role='owner'`.
11. Logout (DevTools POST to `/api/v1/auth/logout` or future logout button) → cookies cleared → root redirects to `/login`.
12. Sign in again — same row returned, no duplicate tenant.
13. Optional — access-token rotation: set `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1` in `.env`, restart backend, wait 90s after login, navigate — verify frontend calls `/refresh` transparently and stays signed in.

## Acceptance criteria

1. `/login` shows a single "Continue with Google" button with Google "G" logo.
2. Clicking it begins Google's OIDC consent flow.
3. Successful consent lands the user on `/` with `access_token` + `refresh_token` HttpOnly cookies set.
4. `GET /api/v1/auth/me` returns the user + tenant info based on cookies alone.
5. First sign-in creates a Tenant + User row with `role='owner'`, `oauth_provider='google'`.
6. Second sign-in reuses the existing row.
7. `POST /api/v1/auth/logout` clears both cookies.
8. Expired access tokens are transparently refreshed via `POST /api/v1/auth/refresh` using the refresh cookie.
9. GitHub buttons and routes are gone from both backend and frontend.
10. CORS is restricted to `settings.app_url` with credentials allowed.
11. All unit tests pass with mocked Authlib. 125 total tests.

## Deferred items (documented, not deliverables of this spec)

- Refresh-token blacklist + reuse detection.
- PKCE extension.
- Email whitelist (restrict tenant creation).
- Logout-everywhere (invalidate all refresh tokens for a user).
- Prometheus counters for auth success/failure.
- Production OAuth consent screen publishing + domain-verified redirect URIs.
- Session lifetime controls (idle timeout, max session age).
- "Remember me" flag to extend refresh TTL.
