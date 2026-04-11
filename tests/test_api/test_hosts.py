import pytest


@pytest.mark.asyncio
async def test_list_hosts_requires_auth(client):
    response = await client.get("/api/v1/hosts")
    assert response.status_code == 403
