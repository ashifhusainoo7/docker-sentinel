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
