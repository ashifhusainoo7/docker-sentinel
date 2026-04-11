import pytest


@pytest.mark.asyncio
async def test_list_crashes_requires_auth(client):
    response = await client.get("/api/v1/crashes")
    assert response.status_code == 403
