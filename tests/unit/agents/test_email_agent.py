from unittest.mock import AsyncMock, patch

import pytest

from src.agents.email_agent import EmailAgent


@pytest.fixture
def agent():
    return EmailAgent(
        host="smtp.test",
        port=587,
        user="sender@test",
        password="secret",
        from_email="sender@test",
    )


@pytest.fixture
def sample_event():
    return {
        "container_name": "web-1",
        "container_id": "abcd1234567890",
        "image": "nginx:1.25",
        "exit_code": 137,
        "logs": "out of memory",
    }


@pytest.fixture
def sample_analysis():
    return {
        "root_cause": "OOM killed during startup",
        "severity": "high",
        "category": "oom",
        "suggestions": ["Raise memory limit", "Investigate leak"],
    }


@pytest.mark.asyncio
async def test_send_renders_template_and_sends(agent, sample_event, sample_analysis):
    with patch("src.agents.email_agent.aiosmtplib.send", new=AsyncMock()) as send:
        result = await agent.send(sample_event, sample_analysis, "dev@test.com")

    assert result is True
    send.assert_awaited_once()
    msg = send.await_args.args[0]
    # The rendered HTML alternative should contain crash fields.
    html_body = msg.get_body(("html",)).get_content()
    assert "web-1" in html_body
    assert "nginx:1.25" in html_body
    assert "137" in html_body
    assert "OOM killed during startup" in html_body
    assert "high" in html_body.lower()  # severity class


@pytest.mark.asyncio
async def test_send_sets_subject_from_container_name(agent, sample_event, sample_analysis):
    with patch("src.agents.email_agent.aiosmtplib.send", new=AsyncMock()) as send:
        await agent.send(sample_event, sample_analysis, "dev@test.com")

    msg = send.await_args.args[0]
    assert "web-1" in msg["Subject"]
    assert "DockerSentinel" in msg["Subject"]
    assert msg["From"] == "sender@test"
    assert msg["To"] == "dev@test.com"


@pytest.mark.asyncio
async def test_send_returns_true_on_success(agent, sample_event, sample_analysis):
    with patch("src.agents.email_agent.aiosmtplib.send", new=AsyncMock()):
        result = await agent.send(sample_event, sample_analysis, "dev@test.com")
    assert result is True


@pytest.mark.asyncio
async def test_send_returns_false_on_smtp_error(agent, sample_event, sample_analysis):
    with patch(
        "src.agents.email_agent.aiosmtplib.send",
        new=AsyncMock(side_effect=RuntimeError("SMTP 535 auth failed")),
    ):
        # Must not raise.
        result = await agent.send(sample_event, sample_analysis, "dev@test.com")
    assert result is False


@pytest.mark.asyncio
async def test_send_returns_false_on_timeout(agent, sample_event, sample_analysis):
    with patch(
        "src.agents.email_agent.aiosmtplib.send",
        new=AsyncMock(side_effect=TimeoutError("hang")),
    ):
        result = await agent.send(sample_event, sample_analysis, "dev@test.com")
    assert result is False


@pytest.mark.asyncio
async def test_send_uses_gmail_defaults_from_init(agent, sample_event, sample_analysis):
    with patch("src.agents.email_agent.aiosmtplib.send", new=AsyncMock()) as send:
        await agent.send(sample_event, sample_analysis, "dev@test.com")

    kwargs = send.await_args.kwargs
    assert kwargs["hostname"] == "smtp.test"
    assert kwargs["port"] == 587
    assert kwargs["username"] == "sender@test"
    assert kwargs["password"] == "secret"
    assert kwargs["start_tls"] is True
