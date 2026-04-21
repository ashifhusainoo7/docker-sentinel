import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def host_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def tenant_id():
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def fake_db_session_factory():
    """Returns a factory that yields a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    factory = MagicMock(return_value=session)
    return factory
