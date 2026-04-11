import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.services.auth_service import create_access_token

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    token = create_access_token(TEST_USER_ID, TEST_TENANT_ID)
    return {"Authorization": f"Bearer {token}"}
