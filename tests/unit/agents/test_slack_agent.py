from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.slack_agent import SlackAgent


@pytest.fixture
def sample_event():
    return {
        "container_name": "web-1",
        "image": "nginx:1.25",
        "exit_code": 137,
    }


@pytest.fixture
def sample_analysis():
    return {
        "root_cause": "OOM killed",
        "severity": "high",
        "category": "oom",
        "suggestions": ["Raise memory limit", "Investigate leak", "Add liveness probe"],
    }


def _mock_client(status_code: int = 200, raise_exc: Exception | None = None):
    """Build a mock httpx.AsyncClient context manager."""
    response = MagicMock()
    response.status_code = status_code
    response.text = f"response text ({status_code})"

    client = AsyncMock()
    if raise_exc is not None:
        client.post = AsyncMock(side_effect=raise_exc)
    else:
        client.post = AsyncMock(return_value=response)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx, client


@pytest.mark.asyncio
async def test_notify_posts_to_webhook_url(sample_event, sample_analysis):
    ctx, client = _mock_client(200)
    agent = SlackAgent(webhook_url="https://hooks.slack.com/services/TEST")

    with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
        result = await agent.notify(sample_event, sample_analysis)

    assert result is True
    client.post.assert_awaited_once()
    args, kwargs = client.post.call_args
    assert args[0] == "https://hooks.slack.com/services/TEST"
    assert "json" in kwargs


@pytest.mark.asyncio
async def test_notify_returns_true_on_2xx(sample_event, sample_analysis):
    for status in [200, 201, 204]:
        ctx, _ = _mock_client(status)
        agent = SlackAgent(webhook_url="https://example.test")
        with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
            assert await agent.notify(sample_event, sample_analysis) is True


@pytest.mark.asyncio
async def test_notify_returns_false_on_4xx(sample_event, sample_analysis):
    ctx, _ = _mock_client(404)
    agent = SlackAgent(webhook_url="https://example.test")
    with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
        assert await agent.notify(sample_event, sample_analysis) is False


@pytest.mark.asyncio
async def test_notify_returns_false_on_5xx(sample_event, sample_analysis):
    ctx, _ = _mock_client(500)
    agent = SlackAgent(webhook_url="https://example.test")
    with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
        assert await agent.notify(sample_event, sample_analysis) is False


@pytest.mark.asyncio
async def test_notify_swallows_network_error(sample_event, sample_analysis):
    ctx, _ = _mock_client(raise_exc=RuntimeError("connection refused"))
    agent = SlackAgent(webhook_url="https://example.test")
    with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
        # Must not raise.
        result = await agent.notify(sample_event, sample_analysis)
    assert result is False


@pytest.mark.asyncio
async def test_block_kit_contains_crash_fields(sample_event, sample_analysis):
    ctx, client = _mock_client(200)
    agent = SlackAgent(webhook_url="https://example.test")
    with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
        await agent.notify(sample_event, sample_analysis)

    payload = client.post.call_args.kwargs["json"]
    serialized = str(payload)
    assert "web-1" in serialized         # container_name
    assert "nginx:1.25" in serialized    # image
    assert "137" in serialized           # exit_code
    assert "HIGH" in serialized          # severity (uppercased)
    assert "OOM killed" in serialized    # root_cause
    assert "oom" in serialized           # category
    assert "Raise memory limit" in serialized  # suggestion


@pytest.mark.asyncio
async def test_block_kit_truncates_suggestions_to_3(sample_event):
    analysis = {
        "root_cause": "x",
        "severity": "high",
        "category": "oom",
        "suggestions": [f"suggestion {i}" for i in range(5)],
    }
    ctx, client = _mock_client(200)
    agent = SlackAgent(webhook_url="https://example.test")
    with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
        await agent.notify(sample_event, analysis)

    payload_str = str(client.post.call_args.kwargs["json"])
    assert "suggestion 0" in payload_str
    assert "suggestion 2" in payload_str
    assert "suggestion 3" not in payload_str
    assert "suggestion 4" not in payload_str


@pytest.mark.asyncio
async def test_block_kit_maps_severity_to_emoji(sample_event):
    mappings = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "⚡",
        "low": "ℹ️",
    }
    for severity, emoji in mappings.items():
        analysis = {"root_cause": "x", "severity": severity, "category": "x", "suggestions": []}
        ctx, client = _mock_client(200)
        agent = SlackAgent(webhook_url="https://example.test")
        with patch("src.agents.slack_agent.httpx.AsyncClient", return_value=ctx):
            await agent.notify(sample_event, analysis)
        payload_str = str(client.post.call_args.kwargs["json"])
        assert emoji in payload_str, f"severity={severity} should contain {emoji}"
