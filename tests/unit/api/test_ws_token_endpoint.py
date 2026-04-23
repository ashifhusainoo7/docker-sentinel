import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.auth import router
from src.services import auth_service
from src.services.auth_cookies import ACCESS_COOKIE


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
    u.is_active = True
    return u


@pytest.mark.asyncio
async def test_ws_token_endpoint_requires_auth(client):
    """POST /ws-token without a cookie should return 401."""
    response = await client.post("/api/v1/auth/ws-token")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ws_token_endpoint_returns_60s_token(client, fake_user):
    """POST /ws-token with valid cookie returns a 60s WS-type JWT."""
    # Build a valid access token to use as the cookie
    access = auth_service.create_access_token(fake_user.id, fake_user.tenant_id)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("src.api.deps.async_session_factory") as factory_mock:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        factory_mock.return_value = mock_session

        response = await client.post(
            "/api/v1/auth/ws-token",
            cookies={ACCESS_COOKIE: access},
        )

    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    assert body["expires_in"] == 60

    # Decode and verify the returned token
    payload = auth_service.decode_token(body["token"])
    assert payload["type"] == "ws"
    assert payload["sub"] == str(fake_user.id)
    assert payload["tenant_id"] == str(fake_user.tenant_id)
    assert payload["exp"] - payload["iat"] == 60
