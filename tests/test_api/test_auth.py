import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_github_login_not_implemented(client):
    response = await client.get("/api/v1/auth/github")
    assert response.status_code == 500  # NotImplementedError
