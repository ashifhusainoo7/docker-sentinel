from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.nodes import notify_slack, send_email


def _config(channel: str, enabled: bool = True, data: dict | None = None):
    c = MagicMock()
    c.channel = channel
    c.is_enabled = enabled
    c.config = data or {}
    return c


# --- notify_slack ---

@pytest.mark.asyncio
async def test_notify_slack_skips_when_no_config(initial_state):
    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=None),
    ), patch("src.orchestrator.nodes.SlackAgent") as Agent:
        result = await notify_slack(initial_state)

    assert result == {"slack_sent": False}
    Agent.assert_not_called()


@pytest.mark.asyncio
async def test_notify_slack_skips_when_webhook_url_missing(initial_state):
    conf = _config("slack", enabled=True, data={})  # no webhook_url
    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=conf),
    ), patch("src.orchestrator.nodes.SlackAgent") as Agent:
        result = await notify_slack(initial_state)

    assert result == {"slack_sent": False}
    Agent.assert_not_called()


@pytest.mark.asyncio
async def test_notify_slack_calls_agent_and_returns_true(initial_state):
    conf = _config("slack", enabled=True, data={"webhook_url": "https://hooks.slack.test/X"})
    fake_agent = MagicMock()
    fake_agent.notify = AsyncMock(return_value=True)

    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=conf),
    ), patch("src.orchestrator.nodes.SlackAgent", return_value=fake_agent) as Agent:
        result = await notify_slack(initial_state)

    assert result == {"slack_sent": True}
    Agent.assert_called_once_with(webhook_url="https://hooks.slack.test/X")
    fake_agent.notify.assert_awaited_once()
    args = fake_agent.notify.await_args.args
    assert args[0] == initial_state["crash_event"]


@pytest.mark.asyncio
async def test_notify_slack_returns_false_on_agent_failure(initial_state):
    conf = _config("slack", enabled=True, data={"webhook_url": "https://example.test"})
    fake_agent = MagicMock()
    fake_agent.notify = AsyncMock(return_value=False)

    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=conf),
    ), patch("src.orchestrator.nodes.SlackAgent", return_value=fake_agent):
        result = await notify_slack(initial_state)

    assert result == {"slack_sent": False}


@pytest.mark.asyncio
async def test_notify_slack_catches_unexpected_exception(initial_state):
    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        # Must not raise.
        result = await notify_slack(initial_state)

    assert result == {"slack_sent": False}


# --- send_email ---

@pytest.mark.asyncio
async def test_send_email_skips_when_no_config(initial_state):
    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=None),
    ), patch("src.orchestrator.nodes.EmailAgent") as Agent:
        result = await send_email(initial_state)

    assert result == {"email_sent": False}
    Agent.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_skips_when_recipient_missing(initial_state):
    conf = _config("email", enabled=True, data={})  # no "to"
    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=conf),
    ), patch("src.orchestrator.nodes.EmailAgent") as Agent:
        result = await send_email(initial_state)

    assert result == {"email_sent": False}
    Agent.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_calls_agent_and_returns_true(initial_state):
    conf = _config("email", enabled=True, data={"to": "dev@test.com"})
    fake_agent = MagicMock()
    fake_agent.send = AsyncMock(return_value=True)

    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=conf),
    ), patch("src.orchestrator.nodes.EmailAgent", return_value=fake_agent):
        result = await send_email(initial_state)

    assert result == {"email_sent": True}
    fake_agent.send.assert_awaited_once()
    args = fake_agent.send.await_args.args
    assert args[0] == initial_state["crash_event"]
    assert args[2] == "dev@test.com"  # recipient


@pytest.mark.asyncio
async def test_send_email_returns_false_on_agent_failure(initial_state):
    conf = _config("email", enabled=True, data={"to": "dev@test.com"})
    fake_agent = MagicMock()
    fake_agent.send = AsyncMock(return_value=False)

    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(return_value=conf),
    ), patch("src.orchestrator.nodes.EmailAgent", return_value=fake_agent):
        result = await send_email(initial_state)

    assert result == {"email_sent": False}


@pytest.mark.asyncio
async def test_send_email_catches_unexpected_exception(initial_state):
    with patch(
        "src.orchestrator.nodes.get_notification_config",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await send_email(initial_state)
    assert result == {"email_sent": False}
