import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.auth import router
from src.services import auth_service
from src.services.auth_cookies import ACCESS_COOKIE, REFRESH_COOKIE


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

        await client.get("/api/v1/auth/google")

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
    token = {"userinfo": {"email": "new@test.com", "name": "New", "picture": None,
                          "sub": "new-sub"}}
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
