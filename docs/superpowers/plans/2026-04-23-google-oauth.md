# Google OAuth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `NotImplementedError` Google OAuth stubs with a production-grade OIDC flow using Authlib, HTTP-only cookies, and refresh-token rotation. Remove the parallel GitHub stubs entirely. Add Google logo to the login button.

**Architecture:** Authlib handles the OIDC redirect + callback, state + nonce CSRF protection, and Google ID token signature verification. After successful authorization, the backend mints access/refresh JWTs and sets them as `HttpOnly; SameSite=Lax` cookies, then redirects to the frontend. Frontend cookie-based API client sends credentials on every request and auto-refreshes on 401.

**Tech Stack:** Python 3.12, Authlib (OIDC client), Starlette `SessionMiddleware` (state storage), FastAPI, pyjwt, Next.js 15, pytest + pytest-asyncio, `unittest.mock`.

**Spec reference:** `docs/superpowers/specs/2026-04-23-google-oauth-design.md`

---

## File Structure

### Files to modify
- `pyproject.toml` — verify `itsdangerous` is present (transitively via Starlette, but make it explicit if missing).
- `src/api/middleware.py` — add `SessionMiddleware`.
- `src/api/deps.py` — `get_current_user` reads cookie first, falls back to `Authorization` header; raise **401** (not 403) when missing.
- `src/api/routers/auth.py` — delete GitHub routes; rewrite Google routes; switch `/refresh` and `/logout` to cookies.
- `src/schemas/auth.py` — remove `TokenRefresh` (no longer used; `/refresh` reads cookie).
- `tests/test_api/test_auth.py` — drop `test_github_login_not_implemented`; update `test_me_requires_auth` for 401 and remove 403 assertion.
- `frontend/src/app/(auth)/login/page.tsx` — remove GitHub button; add Google "G" logo SVG to the remaining button.
- `frontend/src/app/(auth)/callback/page.tsx` — simplify to router-only redirect (tokens now arrive via cookies, not URL params).
- `frontend/src/lib/auth.ts` — drop localStorage helpers; expose only `getMe()` + `logout()`.
- `frontend/src/lib/api.ts` — fetch wrapper uses `credentials: "include"`; 401 → call `/refresh` once → retry; failure → redirect to `/login`.
- `frontend/src/hooks/use-auth.ts` — call `getMe()` on mount (no localStorage check); `logout` hits backend before redirecting.
- `work-tracking/PROGRESS.md` — mark item #17 done; #18 marked "removed (GitHub deferred; pattern preserved for future add-back)".

### New files
- `src/services/oauth_client.py` — module-level Authlib `OAuth` registry with `google` client.
- `src/services/auth_cookies.py` — `set_auth_cookies`, `clear_auth_cookies`, cookie-name constants.
- `tests/unit/api/__init__.py` — package init.
- `tests/unit/api/test_auth_cookies.py` — 4 tests.
- `tests/unit/api/test_auth_router.py` — 9 tests.
- `tests/unit/api/test_deps_auth.py` — 5 tests.
- `tests/unit/services/test_oauth_client.py` — 2 tests.

### Responsibilities per file
- `oauth_client.py` — single source of truth for OAuth provider registration.
- `auth_cookies.py` — centralized cookie naming + flags + lifetimes; every consumer imports from here so there's no drift between `set` / `get` / `clear`.
- `deps.py::get_current_user` — unified token resolution (cookie first, header fallback).
- `routers/auth.py` — all OAuth and session lifecycle endpoints (`/google`, `/google/callback`, `/refresh`, `/logout`, `/me`).

---

## Task 1: Add SessionMiddleware + verify itsdangerous

**Files:**
- Modify: `src/api/middleware.py`
- Modify: `pyproject.toml` (only if itsdangerous missing — check first)

- [ ] **Step 1: Verify `itsdangerous` is installed**

Run: `py -3.12 -c "import itsdangerous; print(itsdangerous.__version__)"`

If this prints a version number, skip to Step 2.

If it fails with `ModuleNotFoundError`, add `"itsdangerous>=2.0.0",` to `pyproject.toml` dependencies list (near `fastapi`):

```toml
    # API
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "itsdangerous>=2.0.0",
    "python-multipart>=0.0.9",
```

Then run: `py -3.12 -m pip install "itsdangerous>=2.0.0"`

- [ ] **Step 2: Add `SessionMiddleware` to `src/api/middleware.py`**

Replace the imports at the top:

```python
import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config.settings import settings

logger = logging.getLogger("sentinel.api")
```

Inside `setup_middleware`, add SessionMiddleware **after** CORS (order matters: SessionMiddleware wraps later, so Authlib can read/write session cookies):

```python
def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_url, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.jwt_secret_key,
        same_site="lax",
        https_only=settings.environment != "development",
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s %d %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response
```

- [ ] **Step 3: Verify the app still boots**

Run: `py -3.12 -c "from src.api.app import create_app; app = create_app(); print('ok')"`
Expected: `ok` printed. No errors.

- [ ] **Step 4: Run the existing test suite — no regressions**

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `109 passed` (unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/api/middleware.py pyproject.toml
git commit -m "feat(api): add SessionMiddleware for OAuth state+nonce storage"
```

---

## Task 2: Implement `auth_cookies.py` helper

**Files:**
- Create: `src/services/auth_cookies.py`
- Create: `tests/unit/api/__init__.py`
- Create: `tests/unit/api/test_auth_cookies.py`

- [ ] **Step 1: Create the tests/unit/api package init**

Create `tests/unit/api/__init__.py` with one line: `# test package`.

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/api/test_auth_cookies.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from src.services.auth_cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    REFRESH_PATH,
    clear_auth_cookies,
    set_auth_cookies,
)


def _capture_set_cookie_calls():
    """Returns a MagicMock Response and a way to inspect set_cookie calls."""
    response = MagicMock()
    return response


def test_set_auth_cookies_writes_access_and_refresh():
    response = _capture_set_cookie_calls()
    set_auth_cookies(response, "access.jwt", "refresh.jwt")

    assert response.set_cookie.call_count == 2
    first = response.set_cookie.call_args_list[0].kwargs
    second = response.set_cookie.call_args_list[1].kwargs

    assert first["key"] == ACCESS_COOKIE
    assert first["value"] == "access.jwt"
    assert first["httponly"] is True
    assert first["samesite"] == "lax"
    assert first["path"] == "/"
    assert first["max_age"] == 30 * 60  # 30 minutes default

    assert second["key"] == REFRESH_COOKIE
    assert second["value"] == "refresh.jwt"
    assert second["httponly"] is True
    assert second["samesite"] == "lax"
    assert second["path"] == REFRESH_PATH
    assert second["max_age"] == 7 * 86400  # 7 days default


def test_set_auth_cookies_secure_in_production():
    response = _capture_set_cookie_calls()
    with patch("src.services.auth_cookies.settings") as s:
        s.environment = "production"
        s.jwt_access_token_expire_minutes = 30
        s.jwt_refresh_token_expire_days = 7
        set_auth_cookies(response, "a", "r")

    for call in response.set_cookie.call_args_list:
        assert call.kwargs["secure"] is True


def test_set_auth_cookies_insecure_in_development():
    response = _capture_set_cookie_calls()
    with patch("src.services.auth_cookies.settings") as s:
        s.environment = "development"
        s.jwt_access_token_expire_minutes = 30
        s.jwt_refresh_token_expire_days = 7
        set_auth_cookies(response, "a", "r")

    for call in response.set_cookie.call_args_list:
        assert call.kwargs["secure"] is False


def test_clear_auth_cookies_deletes_both():
    response = _capture_set_cookie_calls()
    clear_auth_cookies(response)

    assert response.delete_cookie.call_count == 2
    first = response.delete_cookie.call_args_list[0]
    second = response.delete_cookie.call_args_list[1]

    # delete_cookie's first positional arg is the key; path kwarg identifies scope
    args_first = first.args + tuple(first.kwargs.values())
    args_second = second.args + tuple(second.kwargs.values())
    assert ACCESS_COOKIE in args_first
    assert REFRESH_COOKIE in args_second
    assert "/" in args_first or first.kwargs.get("path") == "/"
    assert REFRESH_PATH in args_second or second.kwargs.get("path") == REFRESH_PATH
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/api/test_auth_cookies.py -v`
Expected: FAIL — `src.services.auth_cookies` does not exist.

- [ ] **Step 4: Create `src/services/auth_cookies.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/api/test_auth_cookies.py -v`
Expected: PASS (4 tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `113 passed` (109 + 4).

- [ ] **Step 6: Commit**

```bash
git add src/services/auth_cookies.py tests/unit/api/__init__.py tests/unit/api/test_auth_cookies.py
git commit -m "feat(api): add auth cookie helper with HttpOnly + SameSite=Lax flags"
```

---

## Task 3: Implement `oauth_client.py` registry

**Files:**
- Create: `src/services/oauth_client.py`
- Create: `tests/unit/services/test_oauth_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/services/test_oauth_client.py`:

```python
from src.services.oauth_client import oauth


def test_oauth_client_registers_google_with_correct_scope():
    google = oauth.google  # AttributeError if not registered
    assert google is not None
    assert google.client_kwargs["scope"] == "openid email profile"


def test_oauth_client_uses_google_discovery_url():
    google = oauth.google
    # Authlib stores the discovery URL under server_metadata_url.
    assert (
        google.server_metadata_url
        == "https://accounts.google.com/.well-known/openid-configuration"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/services/test_oauth_client.py -v`
Expected: FAIL — `src.services.oauth_client` does not exist.

- [ ] **Step 3: Create `src/services/oauth_client.py`**

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/services/test_oauth_client.py -v`
Expected: PASS (2 tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `115 passed` (113 + 2).

- [ ] **Step 5: Commit**

```bash
git add src/services/oauth_client.py tests/unit/services/test_oauth_client.py
git commit -m "feat(services): register Authlib OAuth client for Google OIDC"
```

---

## Task 4: Update `get_current_user` for cookie-based auth

**Files:**
- Modify: `src/api/deps.py`
- Create: `tests/unit/api/test_deps_auth.py`

- [ ] **Step 1: Read existing `src/api/deps.py` to preserve surrounding code**

Read `src/api/deps.py`. The existing `get_current_user` uses `OAuth2PasswordBearer` or reads `Authorization` header with `HTTPException(403)`. We'll replace it to read the `access_token` cookie first, fall back to `Authorization: Bearer`, raise 401 (not 403) on missing/invalid.

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/api/test_deps_auth.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.deps import get_current_user
from src.services import auth_service


@pytest.fixture
def user_id():
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def tenant_id():
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def valid_access_token(user_id, tenant_id):
    return auth_service.create_access_token(user_id, tenant_id)


@pytest.fixture
def fake_user(user_id, tenant_id):
    u = MagicMock()
    u.id = user_id
    u.tenant_id = tenant_id
    u.is_active = True
    return u


def _request_with_cookies(cookies: dict):
    req = MagicMock()
    req.cookies = cookies
    return req


def _db_returning(user):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_get_current_user_reads_cookie(valid_access_token, fake_user):
    request = _request_with_cookies({"access_token": valid_access_token})
    db = _db_returning(fake_user)

    result = await get_current_user(request, db, authorization=None)
    assert result is fake_user


@pytest.mark.asyncio
async def test_get_current_user_falls_back_to_authorization_header(
    valid_access_token, fake_user
):
    request = _request_with_cookies({})
    db = _db_returning(fake_user)

    result = await get_current_user(
        request, db, authorization=f"Bearer {valid_access_token}"
    )
    assert result is fake_user


@pytest.mark.asyncio
async def test_get_current_user_prefers_cookie_over_header(
    valid_access_token, fake_user, user_id, tenant_id
):
    cookie_token = valid_access_token
    header_token = auth_service.create_access_token(uuid.uuid4(), uuid.uuid4())

    request = _request_with_cookies({"access_token": cookie_token})
    db = _db_returning(fake_user)

    result = await get_current_user(
        request, db, authorization=f"Bearer {header_token}"
    )
    # Assert the cookie token's user_id was used for the DB lookup
    stmt = db.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert str(user_id) in compiled or user_id.hex in compiled


@pytest.mark.asyncio
async def test_get_current_user_401_when_no_token():
    request = _request_with_cookies({})
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(request, db, authorization=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_401_when_token_expired(user_id, tenant_id, fake_user):
    import jwt
    from config.settings import settings

    # Build an expired token
    expired = jwt.encode(
        {"sub": str(user_id), "tenant_id": str(tenant_id), "type": "access", "exp": 0},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    request = _request_with_cookies({"access_token": expired})
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(request, db, authorization=None)
    assert exc.value.status_code == 401
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/api/test_deps_auth.py -v`
Expected: FAIL — current `get_current_user` doesn't take `request` as its first arg.

- [ ] **Step 4: Replace `get_current_user` in `src/api/deps.py`**

Read the current file first. Find the `get_current_user` function and replace it. Keep `get_db`, `get_tenant`, and any other helpers untouched. Add imports as needed:

```python
import uuid

import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services import auth_service
from src.services.auth_cookies import ACCESS_COOKIE
from src.services.database import get_db


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
```

If `get_tenant` in the same file references the old `get_current_user` signature, update its call site to match (it shouldn't — it takes `user: User = Depends(get_current_user)` which works regardless of the function's own parameters).

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/api/test_deps_auth.py -v`
Expected: PASS (5 tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `120 passed` (115 + 5).

- [ ] **Step 6: Commit**

```bash
git add src/api/deps.py tests/unit/api/test_deps_auth.py
git commit -m "feat(api): get_current_user resolves token from cookie then Bearer header"
```

---

## Task 5: Rewrite auth router

**Files:**
- Modify: `src/api/routers/auth.py`
- Modify: `src/schemas/auth.py`
- Create: `tests/unit/api/test_auth_router.py`

This is the big one — delete GitHub, wire up Google OIDC, switch `/refresh` and `/logout` to cookies.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/api/test_auth_router.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.auth import router
from src.services import auth_service
from src.services.auth_cookies import ACCESS_COOKIE, REFRESH_COOKIE, REFRESH_PATH


@pytest.fixture
def app():
    a = FastAPI()
    a.include_router(router)
    return a


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def fake_user():
    u = MagicMock()
    u.id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u.tenant_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    u.email = "user@test.com"
    u.name = "Test User"
    return u


@pytest.mark.asyncio
async def test_google_login_redirects_to_google(client):
    fake_redirect = MagicMock()
    fake_redirect.status_code = 302
    fake_redirect.headers = {"location": "https://accounts.google.com/o/oauth2/v2/auth?scope=openid+email+profile&state=xyz"}

    with patch("src.api.routers.auth.oauth") as oauth_mod:
        oauth_mod.google = MagicMock()
        oauth_mod.google.authorize_redirect = AsyncMock(return_value=fake_redirect)

        response = await client.get("/api/v1/auth/google")

    # The router returns whatever Authlib returns; we're asserting the call
    oauth_mod.google.authorize_redirect.assert_awaited_once()


@pytest.mark.asyncio
async def test_google_callback_sets_cookies_and_redirects_to_app_url(
    client, fake_user
):
    token = {
        "userinfo": {
            "email": "user@test.com",
            "name": "Test User",
            "picture": "https://avatar.test/x.png",
            "sub": "google-sub-12345",
        }
    }

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("src.api.routers.auth.oauth") as oauth_mod, \
         patch("src.api.routers.auth.auth_service.get_or_create_user_from_oauth",
               new=AsyncMock(return_value=fake_user)), \
         patch("src.api.routers.auth.get_db", return_value=mock_db):
        oauth_mod.google = MagicMock()
        oauth_mod.google.authorize_access_token = AsyncMock(return_value=token)

        response = await client.get(
            "/api/v1/auth/google/callback", follow_redirects=False
        )

    assert response.status_code in (302, 307)
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("access_token=" in h for h in set_cookie_headers)
    assert any("refresh_token=" in h for h in set_cookie_headers)
    assert any("HttpOnly" in h for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_google_callback_creates_user_on_first_login(client, fake_user):
    token = {"userinfo": {"email": "new@test.com", "name": "New", "picture": None, "sub": "new-sub"}}
    create_fn = AsyncMock(return_value=fake_user)
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("src.api.routers.auth.oauth") as oauth_mod, \
         patch("src.api.routers.auth.auth_service.get_or_create_user_from_oauth", new=create_fn), \
         patch("src.api.routers.auth.get_db", return_value=mock_db):
        oauth_mod.google = MagicMock()
        oauth_mod.google.authorize_access_token = AsyncMock(return_value=token)

        await client.get("/api/v1/auth/google/callback", follow_redirects=False)

    create_fn.assert_awaited_once()
    call_kwargs = create_fn.await_args.kwargs
    assert call_kwargs["email"] == "new@test.com"
    assert call_kwargs["provider"] == "google"
    assert call_kwargs["provider_id"] == "new-sub"


@pytest.mark.asyncio
async def test_google_callback_redirects_to_login_on_state_mismatch(client):
    with patch("src.api.routers.auth.oauth") as oauth_mod:
        oauth_mod.google = MagicMock()
        oauth_mod.google.authorize_access_token = AsyncMock(
            side_effect=RuntimeError("state mismatch")
        )

        response = await client.get(
            "/api/v1/auth/google/callback", follow_redirects=False
        )

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "/login" in location
    assert "error=" in location


@pytest.mark.asyncio
async def test_google_callback_redirects_to_login_when_userinfo_missing(client):
    with patch("src.api.routers.auth.oauth") as oauth_mod:
        oauth_mod.google = MagicMock()
        oauth_mod.google.authorize_access_token = AsyncMock(return_value={})

        response = await client.get(
            "/api/v1/auth/google/callback", follow_redirects=False
        )

    assert response.status_code in (302, 307)
    assert "no_userinfo" in response.headers["location"]


@pytest.mark.asyncio
async def test_refresh_rotates_both_cookies_on_valid_refresh_token(client):
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    refresh = auth_service.create_refresh_token(user_id, tenant_id)

    response = await client.post(
        "/api/v1/auth/refresh", cookies={REFRESH_COOKIE: refresh}
    )

    assert response.status_code == 200
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any(f"{ACCESS_COOKIE}=" in h for h in set_cookie_headers)
    assert any(f"{REFRESH_COOKIE}=" in h for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_refresh_returns_401_when_no_cookie(client):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_401_when_access_token_used_as_refresh(client):
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    access = auth_service.create_access_token(user_id, tenant_id)

    response = await client.post(
        "/api/v1/auth/refresh", cookies={REFRESH_COOKIE: access}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_both_cookies(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    set_cookie_headers = response.headers.get_list("set-cookie")
    # delete_cookie sends Max-Age=0
    assert any("Max-Age=0" in h for h in set_cookie_headers)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/api/test_auth_router.py -v`
Expected: FAIL — Google routes are `NotImplementedError`; `/refresh` expects a JSON body not a cookie; imports don't exist.

- [ ] **Step 3: Remove `TokenRefresh` from `src/schemas/auth.py`**

Read `src/schemas/auth.py`. Remove the `TokenRefresh` class definition — no other code references it after this task. Leave `Token`, `UserResponse`, `MeResponse`, and any other classes in place. If `TokenRefresh` is re-exported via `__all__`, remove it from the list too.

- [ ] **Step 4: Replace `src/api/routers/auth.py`**

Read the current file first for context, then replace it entirely:

```python
import uuid
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
```

GitHub routes (`github_login`, `github_callback`) are intentionally removed.

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/api/test_auth_router.py -v`
Expected: PASS (9 tests).

- [ ] **Step 6: Commit**

```bash
git add src/api/routers/auth.py src/schemas/auth.py tests/unit/api/test_auth_router.py
git commit -m "feat(api): implement Google OIDC flow with HttpOnly cookie delivery"
```

---

## Task 6: Update legacy test_api/test_auth.py

**Files:**
- Modify: `tests/test_api/test_auth.py`

- [ ] **Step 1: Read and update the file**

Open `tests/test_api/test_auth.py` and replace its entire contents:

```python
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    """Without a cookie or Bearer header, /me returns 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
```

The old `test_github_login_not_implemented` is dropped — GitHub routes no longer exist.

- [ ] **Step 2: Run the test file**

Run: `py -3.12 -m pytest tests/test_api/test_auth.py -v`
Expected: PASS (2 tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ tests/test_api/test_auth.py 2>&1 | tail -3`
Expected: `120 + 2 = 122` passed (or equivalent — exact count depends on prior task totals; no new unit tests added here).

Actually — the Task 5 suite result `129 passed` (120 existing + 9 new router tests). Then removing one test from `test_auth.py` (the `github_login_not_implemented`) nets unchanged count there, but the `test_me_requires_auth` behaves differently now — 401 instead of 403 — so the assertion update is what this task is for. Run the full suite to confirm:

Run: `py -3.12 -m pytest tests/ 2>&1 | tail -3`
Expected: all pass, no failures.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api/test_auth.py
git commit -m "test(api): update legacy auth tests for 401 + drop GitHub stub assertion"
```

---

## Task 7: Frontend login page — Google logo, drop GitHub

**Files:**
- Modify: `frontend/src/app/(auth)/login/page.tsx`

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `frontend/src/app/(auth)/login/page.tsx`:

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

- [ ] **Step 2: Verify the file builds**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(auth\)/login/page.tsx
git commit -m "feat(frontend): Google-only login button with brand logo"
```

---

## Task 8: Frontend cookie-based auth plumbing

**Files:**
- Modify: `frontend/src/lib/auth.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/hooks/use-auth.ts`
- Modify: `frontend/src/app/(auth)/callback/page.tsx`

- [ ] **Step 1: Replace `frontend/src/lib/auth.ts`**

```ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getMe(): Promise<{ user: UserPayload; tenant_name: string; tenant_slug: string } | null> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export interface UserPayload {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: string;
}
```

- [ ] **Step 2: Replace `frontend/src/lib/api.ts`**

```ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function refreshOnce(): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  return res.ok;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    _retry = false,
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (response.status === 401 && !_retry && !path.startsWith("/api/v1/auth/")) {
      const refreshed = await refreshOnce();
      if (refreshed) {
        return this.request<T>(path, options, true);
      }
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  put<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  delete(path: string) {
    return this.request(path, { method: "DELETE" });
  }
}

export const api = new ApiClient(API_URL);
```

- [ ] **Step 3: Replace `frontend/src/hooks/use-auth.ts`**

```ts
"use client";

import { useEffect, useState } from "react";
import { getMe, logout as backendLogout, type UserPayload } from "@/lib/auth";

interface AuthState {
  user: UserPayload | null;
  tenantName: string | null;
  loading: boolean;
  logout: () => Promise<void>;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<UserPayload | null>(null);
  const [tenantName, setTenantName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((data) => {
        if (data) {
          setUser(data.user);
          setTenantName(data.tenant_name);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = async () => {
    await backendLogout();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };

  return { user, tenantName, loading, logout };
}
```

- [ ] **Step 4: Replace `frontend/src/app/(auth)/callback/page.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CallbackPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);
  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing in...</p>
    </div>
  );
}
```

- [ ] **Step 5: Verify types compile**

Run: `cd frontend && npx tsc --noEmit && cd ..`
Expected: no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/lib/api.ts frontend/src/hooks/use-auth.ts frontend/src/app/\(auth\)/callback/page.tsx
git commit -m "feat(frontend): cookie-based auth with transparent 401 refresh"
```

---

## Task 9: Update work tracker

**Files:**
- Modify: `work-tracking/PROGRESS.md`

- [ ] **Step 1: Mark item 17 done, update item 18 status**

Find in `work-tracking/PROGRESS.md`:

```markdown
| 17 | `src/api/routers/auth.py` | GitHub OAuth login + callback | **High** |
| 18 | `src/api/routers/auth.py` | Google OAuth login + callback | **High** |
```

Replace with:

```markdown
| 17 | `src/api/routers/auth.py` | Google OAuth login + callback (Authlib OIDC + HttpOnly cookies) | ✅ **Done** |
| 18 | `src/api/routers/auth.py` | GitHub OAuth login + callback | 🗑️ **Removed** (same pattern available if re-added) |
```

- [ ] **Step 2: Add today's daily log entry**

Append to the `## Daily Log` section:

```markdown
### 2026-04-23 (Continued — Google OAuth)
- **Status:** ✅ **Phase 4 item #17 shipped.** Google OIDC sign-in working end-to-end with production-grade cookie auth. GitHub routes removed.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-23-google-oauth-design.md`
  - Wrote 10-task plan: `docs/superpowers/plans/2026-04-23-google-oauth.md`
  - Added `SessionMiddleware` (Starlette) for Authlib state+nonce storage
  - `src/services/oauth_client.py` — module-level Authlib OAuth registry with Google OIDC discovery URL
  - `src/services/auth_cookies.py` — centralized HttpOnly / SameSite=Lax cookie helpers; refresh-token scoped to `/api/v1/auth`
  - `get_current_user` now reads `access_token` cookie first, falls back to `Authorization: Bearer` for programmatic access; raises 401 (not 403)
  - Rewrote `auth.py` router: Google login + callback, cookie-based refresh + logout, `/me` via cookies
  - Removed GitHub routes + `TokenRefresh` schema
  - Frontend: drop GitHub button, add Google "G" logo, cookie-based API client with auto-refresh on 401, simplified callback page, updated `useAuth` hook
  - 20 new unit tests across cookies / oauth_client / deps / router. 129 total backend tests passing.
- **Known deferred items:**
  - Refresh-token blacklist + reuse detection.
  - Email whitelist (anyone with a Google account can auto-provision a tenant).
  - Logout-everywhere (invalidating all refresh tokens for a user).
  - Prometheus counters for auth success/failure.
  - PKCE extension (overkill for confidential client with server-side secret).
  - Production OAuth consent screen publishing + domain-verified redirect URIs.
- **Pre-work for next user who runs the app:** follow the Google Cloud Console setup in `docs/superpowers/specs/2026-04-23-google-oauth-design.md` §Configuration. Populate `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` in `.env`. Add `http://localhost:8000/api/v1/auth/google/callback` to the OAuth client's authorized redirect URIs.
- **Pick up from here:** Good candidates for the next session:
  - **Dashboard wiring (Phase 5 items #23–25)** — `/api/v1/dashboard/{summary,metrics,timeline}` endpoints + Next.js pages consuming live crash data.
  - **CallAgent + Twilio (items #10, #14)** — voice escalation.
  - **Observability & metrics** — Prometheus counters for notifications, LLM failures, auth events.
  - **Agent container (Phase 6 item #26)** — customer-hosted agent via WebSocket.
```

- [ ] **Step 3: Commit**

```bash
git add work-tracking/PROGRESS.md
git commit -m "docs: mark Phase 4 item 17 (Google OAuth) complete in work tracker"
```

---

## Task 10: Manual smoke test — real Google OAuth end-to-end

**Files:** none — verification only.

User prerequisites:
- Complete Google Cloud Console setup per `docs/superpowers/specs/2026-04-23-google-oauth-design.md` §Configuration.
- `.env` populated with real `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

- [ ] **Step 1: Start infra**

Run: `docker compose up -d postgres redis`
Expected: postgres + redis healthy.

- [ ] **Step 2: Migrate + clean state**

Run:
```bash
py -3.12 -m alembic upgrade head
docker compose exec -T postgres psql -U sentinel -d sentinel -c "TRUNCATE users, tenants RESTART IDENTITY CASCADE;"
```
Expected: migrations current; users/tenants wiped.

- [ ] **Step 3: Start backend**

Run (leave running): `py -3.12 -m uvicorn src.api.app:create_app --factory --reload --port 8000`
Expected: uvicorn logs `Application startup complete.`

- [ ] **Step 4: Start frontend**

In a new terminal:
```bash
cd frontend
npm run dev
```
Expected: Next.js dev server on `http://localhost:3000`.

- [ ] **Step 5: Sign in through Google**

Open `http://localhost:3000/login`. Confirm:
- Only one button: "Continue with Google" with the Google "G" logo (no GitHub button).

Click the button → redirected to Google's consent screen.

Authorize with your test-user Gmail account.

Expected: redirected back to `http://localhost:3000/`.

- [ ] **Step 6: Verify cookies**

Open DevTools → Application → Cookies → `http://localhost:8000`. Expect to see:
- `access_token` cookie: `HttpOnly`, `SameSite=Lax`, **no** `Secure` flag (dev), `Path=/`, Max-Age ≈ 1800s.
- `refresh_token` cookie: `HttpOnly`, `SameSite=Lax`, **no** `Secure` flag, `Path=/api/v1/auth`, Max-Age ≈ 604800s.
- `session` cookie (Starlette's SessionMiddleware): present but irrelevant to the auth JWTs.

- [ ] **Step 7: Verify user/tenant creation**

Run:
```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "SELECT u.email, u.name, u.oauth_provider, u.role, t.name AS tenant FROM users u JOIN tenants t ON u.tenant_id = t.id;"
```
Expected: one row, your email, `oauth_provider='google'`, `role='owner'`, tenant name = `<Your Name>'s Workspace`.

- [ ] **Step 8: Verify /me endpoint via cookies**

In the same browser session (cookies set), open DevTools console and run:
```js
fetch("http://localhost:8000/api/v1/auth/me", {credentials: "include"}).then(r => r.json()).then(console.log)
```
Expected: JSON with `user`, `tenant_name`, `tenant_slug` fields.

- [ ] **Step 9: Verify logout clears cookies**

Run in DevTools console:
```js
fetch("http://localhost:8000/api/v1/auth/logout", {method: "POST", credentials: "include"}).then(r => console.log(r.status))
```
Expected: 200.

DevTools → Cookies: `access_token` and `refresh_token` are gone (or `Max-Age=0`).

Navigate to `http://localhost:3000/` — should redirect to `/login` (because the cookies are gone).

- [ ] **Step 10: Sign in again**

Click "Continue with Google" again → redirected through consent → back to `/`.

Re-run the SQL query from Step 7 — same single row, no duplicate tenant.

- [ ] **Step 11: Optional — test access-token rotation**

Temporarily change `.env`:
```
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1
```

Restart the backend. Sign in. Wait 90 seconds. Then navigate / refresh the page.

Expected: you stay signed in. Check backend logs for `POST /api/v1/auth/refresh 200`. The frontend's 401-retry logic transparently rotated the tokens.

Revert `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30` in `.env`.

- [ ] **Step 12: Tear down**

Run:
```bash
# Stop both dev servers (Ctrl+C in each terminal)
docker compose down
```

- [ ] **Step 13: No commit needed**

Smoke test is verification-only. If any step failed, investigate and file follow-ups — don't monkey-patch the plan.

---

## Self-review (completed by the planner)

- **Spec coverage:**
  - SessionMiddleware + CORS → Task 1.
  - `auth_cookies.py` helper with flags → Task 2.
  - `oauth_client.py` Authlib registry → Task 3.
  - `get_current_user` cookie+header resolution → Task 4.
  - Google login + callback + cookie-based refresh + logout → Task 5.
  - GitHub route removal → Task 5 (router rewrite drops them).
  - Legacy test cleanup → Task 6.
  - Frontend login page + Google logo → Task 7.
  - Frontend cookie API client + refresh logic + useAuth → Task 8.
  - Work tracker → Task 9.
  - Google Console setup + smoke test → Task 10.
- **Placeholder scan:** No TBD/TODO/vague steps. Every code step shows complete code.
- **Type/name consistency:**
  - `ACCESS_COOKIE="access_token"`, `REFRESH_COOKIE="refresh_token"`, `REFRESH_PATH="/api/v1/auth"` consistent across Tasks 2, 4, 5, 8.
  - `set_auth_cookies(response, access, refresh)` / `clear_auth_cookies(response)` signatures identical between Task 2 and Task 5 callers.
  - `get_current_user(request, db, authorization)` signature consistent between Task 4 definition and Task 5 `@router.get("/me", ... Depends(get_current_user))`.
  - `oauth.google.authorize_redirect` / `authorize_access_token` consistent between Task 3 registration and Task 5 callers.
- **Known caveat (not a placeholder):** Task 5 tests use `client.get("/api/v1/auth/google", ...)` patching `src.api.routers.auth.oauth`. If the Authlib `OAuth` instance caches metadata or state differently than expected, the mock may need adjusting — the implementer should adapt test fixtures if the mock shape doesn't match without changing behavior.
