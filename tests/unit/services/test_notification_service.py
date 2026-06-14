import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.notification_service import get_notification_config


def _factory(rows):
    """Build an async_sessionmaker-shaped mock that returns `rows` on
    execute().scalar_one_or_none()."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    session.execute = AsyncMock(return_value=result)
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return MagicMock(return_value=session)


@pytest.mark.asyncio
async def test_returns_row_when_enabled():
    row = MagicMock()
    row.channel = "slack"
    row.is_enabled = True
    factory = _factory([row])

    result = await get_notification_config(factory, uuid.uuid4(), "slack")
    assert result is row


@pytest.mark.asyncio
async def test_returns_none_when_no_row():
    factory = _factory([])
    result = await get_notification_config(factory, uuid.uuid4(), "slack")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_db_has_only_disabled_rows():
    """The SQL filter excludes is_enabled=False rows; scalar_one_or_none returns None."""
    factory = _factory([])  # simulates the post-filter result
    result = await get_notification_config(factory, uuid.uuid4(), "slack")
    assert result is None


@pytest.mark.asyncio
async def test_channel_filter_reaches_sql():
    factory = _factory([])
    tenant = uuid.uuid4()
    await get_notification_config(factory, tenant, "email")

    session = factory.return_value
    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "notification_configs" in compiled
    assert "'email'" in compiled
    assert "is_enabled" in compiled


@pytest.mark.asyncio
async def test_tenant_filter_reaches_sql():
    factory = _factory([])
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    await get_notification_config(factory, tenant, "slack")

    session = factory.return_value
    stmt = session.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    # SQLAlchemy may render UUID with or without hyphens depending on dialect
    assert str(tenant) in compiled or tenant.hex in compiled
