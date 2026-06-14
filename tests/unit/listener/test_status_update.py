from unittest.mock import AsyncMock, MagicMock

import pytest

from src.listener._status import update_host_status


@pytest.mark.asyncio
async def test_update_host_status_writes_to_db(host_id, fake_db_session_factory):
    await update_host_status(
        fake_db_session_factory, host_id, "connected", None
    )

    session = fake_db_session_factory.return_value
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_host_status_swallows_db_errors(host_id, caplog):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    factory = MagicMock(return_value=session)

    # must not raise
    await update_host_status(factory, host_id, "error", "oops")
    assert "Failed to update status" in caplog.text
