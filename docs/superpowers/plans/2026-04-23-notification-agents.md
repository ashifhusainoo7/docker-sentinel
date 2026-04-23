# Notification Agents (Slack + Email) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `SlackAgent` + `EmailAgent` and wire them through the orchestrator so a non-restart-fixable crash (or failed restart) produces real Slack messages and real emails. Restore the `False → notify_slack` graph edges stubbed out in Phase 2.

**Architecture:** Two new agent classes (httpx-based Slack webhook posts; aiosmtplib + Jinja2 email). A tiny helper `get_notification_config` on the service layer reads per-tenant `NotificationConfig` rows. `notify_slack` and `send_email` nodes wrap delivery with outer exception guards so the graph never dies in a notification step. `should_restart` and `check_restart_result` conditional edges restored to route non-restart paths to `"notify_slack"`.

**Tech Stack:** Python 3.11, `httpx`, `aiosmtplib` (new), Jinja2, SQLAlchemy async, pytest + pytest-asyncio, `unittest.mock`.

**Spec reference:** `docs/superpowers/specs/2026-04-23-notification-agents-design.md`

---

## File Structure

### Files to modify
- `pyproject.toml` — add `aiosmtplib>=3.0.0`.
- `config/settings.py` — add `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`.
- `src/agents/slack_agent.py` — full rewrite with real webhook POST.
- `src/agents/email_agent.py` — full rewrite with Jinja2 template render + aiosmtplib send.
- `src/services/notification_service.py` — add `get_notification_config` helper.
- `src/orchestrator/nodes.py` — rewrite `notify_slack`, `send_email`, restore `should_restart` and `check_restart_result`.
- `src/orchestrator/graph.py` — restore `"notify_slack": "slack"` mapping on `analyze` and `restart` conditional edges.
- `tests/unit/orchestrator/test_conditional_edges.py` — update existing tests for the new `"notify_slack"` return on False branches.
- `tests/unit/orchestrator/test_workflow_end_to_end.py` — update existing happy-path assertions; add 2 new scenarios covering the notification path.
- `work-tracking/PROGRESS.md` — mark items 8, 9, 12, 13 done; add daily log entry.

### Files to create
- `tests/unit/agents/test_slack_agent.py` — 8 tests.
- `tests/unit/agents/test_email_agent.py` — 6 tests.
- `tests/unit/services/test_notification_service.py` — 5 tests.
- `tests/unit/orchestrator/test_notification_nodes.py` — 10 tests.

### Responsibilities per file
- `slack_agent.py` — one class, `notify(crash_event, analysis) -> bool`. Never raises past its return.
- `email_agent.py` — one class, `send(crash_event, analysis, recipient_email) -> bool`. Never raises.
- `notification_service.py` — thin DB helper. Returns `NotificationConfig | None`.
- `nodes.py` — orchestrator-glue. Nodes catch everything; conditional edges are pure functions.
- `graph.py` — edge mappings only.

---

## Task 1: Add `aiosmtplib` dep + SMTP settings

**Files:**
- Modify: `pyproject.toml`
- Modify: `config/settings.py`

- [ ] **Step 1: Add dep to `pyproject.toml`**

Locate the `dependencies = [...]` list. Find the `"jinja2>=3.1.0"` line under `# Notifications` and add `aiosmtplib` right after it:

```toml
    # Notifications
    "jinja2>=3.1.0",
    "aiosmtplib>=3.0.0",
    "twilio>=9.0.0",
```

- [ ] **Step 2: Install the dep**

Run: `py -3.12 -m pip install "aiosmtplib>=3.0.0"`
Expected: installs aiosmtplib (small pure-Python package; takes ~5s).

- [ ] **Step 3: Verify import works**

Run: `py -3.12 -c "import aiosmtplib; print(aiosmtplib.__version__)"`
Expected: prints a version number (e.g., `3.0.2`). No error.

- [ ] **Step 4: Add SMTP settings to `config/settings.py`**

Find the existing `smtp_from_email: str = ""` line (around line 42). Replace that block of notification settings so it reads:

```python
    # Notifications — Platform Defaults
    slack_webhook_url: str = ""
    sendgrid_api_key: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
```

(Only the four smtp_host/smtp_port/smtp_user/smtp_password lines are new; leave everything else in that block as-is.)

- [ ] **Step 5: Verify settings import cleanly**

Run: `py -3.12 -c "from config.settings import settings; print(settings.smtp_host, settings.smtp_port)"`
Expected: prints `smtp.gmail.com 587`.

- [ ] **Step 6: Run the suite — no regressions**

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: 76 passed (same as baseline).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml config/settings.py
git commit -m "chore(deps): add aiosmtplib and Gmail SMTP settings"
```

---

## Task 2: Implement `SlackAgent`

**Files:**
- Modify: `src/agents/slack_agent.py` (full rewrite)
- Create: `tests/unit/agents/test_slack_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/agents/test_slack_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/agents/test_slack_agent.py -v`
Expected: FAIL — current `SlackAgent.notify` raises `NotImplementedError`.

- [ ] **Step 3: Replace `src/agents/slack_agent.py`**

Replace the entire contents:

```python
import logging
from typing import Any

import httpx

logger = logging.getLogger("sentinel.agents.slack")


class SlackAgent:
    """Sends immediate crash alerts to Slack channels via webhooks.

    Uses Block Kit formatting for readable notifications. All delivery
    errors are swallowed — notify returns False on any failure.
    """

    def __init__(self, webhook_url: str, timeout_s: float = 10.0):
        self.webhook_url = webhook_url
        self.timeout_s = timeout_s

    async def notify(self, crash_event: dict, analysis: dict) -> bool:
        """Returns True on 2xx webhook response, False on any failure."""
        payload = self._build_block_kit(crash_event, analysis)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(self.webhook_url, json=payload)
            if 200 <= resp.status_code < 300:
                return True
            logger.warning(
                "Slack webhook returned %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        except Exception:
            logger.exception("Slack webhook call failed")
            return False

    def _build_block_kit(
        self, crash_event: dict, analysis: dict
    ) -> dict[str, Any]:
        severity = (analysis.get("severity") or "unknown").upper()
        emoji = {
            "CRITICAL": "🚨",
            "HIGH": "⚠️",
            "MEDIUM": "⚡",
            "LOW": "ℹ️",
        }.get(severity, "❓")
        suggestions = analysis.get("suggestions") or []
        suggestion_text = (
            "\n".join(f"• {s}" for s in suggestions[:3]) or "_None_"
        )

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Container Crash: {crash_event.get('container_name', 'unknown')}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Image:*\n{crash_event.get('image', 'unknown')}"},
                        {"type": "mrkdwn", "text": f"*Exit Code:*\n{crash_event.get('exit_code')}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                        {"type": "mrkdwn", "text": f"*Category:*\n{analysis.get('category', 'unknown')}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause:*\n{analysis.get('root_cause', 'Unknown')}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Suggested Fixes:*\n{suggestion_text}",
                    },
                },
            ]
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/agents/test_slack_agent.py -v`
Expected: PASS (8 tests).

Run full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `84 passed` (76 + 8).

- [ ] **Step 5: Commit**

```bash
git add src/agents/slack_agent.py tests/unit/agents/test_slack_agent.py
git commit -m "feat(agents): implement SlackAgent with Block Kit webhook POST"
```

---

## Task 3: Implement `EmailAgent`

**Files:**
- Modify: `src/agents/email_agent.py` (full rewrite)
- Create: `tests/unit/agents/test_email_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/agents/test_email_agent.py`:

```python
import asyncio
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
        new=AsyncMock(side_effect=asyncio.TimeoutError("hang")),
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/agents/test_email_agent.py -v`
Expected: FAIL — current `EmailAgent.send` raises `NotImplementedError` and lacks the new constructor signature.

- [ ] **Step 3: Replace `src/agents/email_agent.py`**

Replace the entire contents:

```python
import logging
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings

logger = logging.getLogger("sentinel.agents.email")


class EmailAgent:
    """Sends HTML crash reports via SMTP (default: Gmail).

    Renders `src/templates/crash_email.html` with Jinja2 then delivers
    through `aiosmtplib.send` with STARTTLS. All delivery errors are
    swallowed — send returns False on any failure.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
        timeout_s: float = 15.0,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.timeout_s = timeout_s
        self._env = Environment(
            loader=FileSystemLoader("src/templates"),
            autoescape=select_autoescape(["html"]),
        )

    async def send(
        self, crash_event: dict, analysis: dict, recipient_email: str
    ) -> bool:
        """Returns True on successful SMTP send, False on any failure."""
        try:
            template = self._env.get_template("crash_email.html")
            html = template.render(
                event=crash_event,
                analysis=analysis,
                summary=None,
                dashboard_url=settings.app_url,
            )
            msg = EmailMessage()
            msg["From"] = self.from_email
            msg["To"] = recipient_email
            msg["Subject"] = (
                f"[DockerSentinel] Crash: "
                f"{crash_event.get('container_name', 'unknown')}"
            )
            msg.set_content("View this email in an HTML-capable client.")
            msg.add_alternative(html, subtype="html")

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
                timeout=self.timeout_s,
            )
            return True
        except Exception:
            logger.exception("Email send failed")
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/agents/test_email_agent.py -v`
Expected: PASS (6 tests).

Run full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `90 passed` (84 + 6).

- [ ] **Step 5: Commit**

```bash
git add src/agents/email_agent.py tests/unit/agents/test_email_agent.py
git commit -m "feat(agents): implement EmailAgent with Jinja2 template + aiosmtplib"
```

---

## Task 4: `get_notification_config` helper

**Files:**
- Modify: `src/services/notification_service.py`
- Create: `tests/unit/services/test_notification_service.py`

- [ ] **Step 1: Inspect existing `notification_service.py`**

Read `src/services/notification_service.py` to confirm its current shape. If it contains an existing `test_notification` function with `NotImplementedError`, leave that as-is (out of scope for this plan). We only ADD `get_notification_config` — we don't replace the file.

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/services/test_notification_service.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.notification_service import get_notification_config


def _factory(rows):
    """Build an async_sessionmaker-shaped mock that returns `rows` on execute().scalar_one_or_none()."""
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
    assert str(tenant) in compiled
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/services/test_notification_service.py -v`
Expected: FAIL — `get_notification_config` doesn't exist yet.

- [ ] **Step 4: Add the helper to `src/services/notification_service.py`**

Append these additions to the top of `src/services/notification_service.py` (preserving any existing content below):

```python
import uuid

from sqlalchemy import select

from src.models.notification_config import NotificationConfig


async def get_notification_config(
    session_factory,
    tenant_id: uuid.UUID,
    channel: str,
) -> NotificationConfig | None:
    """Return an enabled NotificationConfig for (tenant, channel), or None."""
    async with session_factory() as session:
        result = await session.execute(
            select(NotificationConfig).where(
                NotificationConfig.tenant_id == tenant_id,
                NotificationConfig.channel == channel,
                NotificationConfig.is_enabled == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
```

If `src/services/notification_service.py` already has an `import uuid` or imports `select` from `sqlalchemy`, don't duplicate. If it's currently empty or has only a class/function definition, just prepend the new imports + function at the top, above any existing code.

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/services/test_notification_service.py -v`
Expected: PASS (5 tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `95 passed` (90 + 5).

- [ ] **Step 6: Commit**

```bash
git add src/services/notification_service.py tests/unit/services/test_notification_service.py
git commit -m "feat(services): add get_notification_config helper for tenant+channel lookup"
```

---

## Task 5: Restore `should_restart` + `check_restart_result` routing, update graph

**Files:**
- Modify: `src/orchestrator/nodes.py`
- Modify: `src/orchestrator/graph.py`
- Modify: `tests/unit/orchestrator/test_conditional_edges.py`

The conditional-edge functions currently route non-restart paths to `"log"` as a Phase 2 workaround. Restore them to return `"notify_slack"`, and update the graph mappings so LangGraph knows where to route that key. Because notify_slack is still `NotImplementedError` until Task 6, do Task 5 and Task 6 as separate commits but run the E2E test only AFTER Task 6.

- [ ] **Step 1: Update `test_conditional_edges.py` tests**

Replace the entire contents of `tests/unit/orchestrator/test_conditional_edges.py`:

```python
from src.orchestrator.nodes import check_restart_result, should_restart


# --- check_restart_result ---

def test_check_restart_result_true_goes_to_log():
    assert check_restart_result({"restart_success": True}) == "log"


def test_check_restart_result_false_goes_to_notify_slack():
    assert check_restart_result({"restart_success": False}) == "notify_slack"


def test_check_restart_result_none_goes_to_notify_slack():
    """Defensive: when restart wasn't attempted (host missing, non-TCP), also notify."""
    assert check_restart_result({"restart_success": None}) == "notify_slack"


def test_check_restart_result_missing_key_goes_to_notify_slack():
    assert check_restart_result({}) == "notify_slack"


# --- should_restart ---

def test_should_restart_true_goes_to_attempt_restart():
    state = {"analysis": {"restart_likely_fixes": True}}
    assert should_restart(state) == "attempt_restart"


def test_should_restart_false_goes_to_notify_slack():
    state = {"analysis": {"restart_likely_fixes": False}}
    assert should_restart(state) == "notify_slack"


def test_should_restart_missing_analysis_goes_to_notify_slack():
    assert should_restart({"analysis": None}) == "notify_slack"
    assert should_restart({}) == "notify_slack"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_conditional_edges.py -v`
Expected: FAIL — `should_restart` and `check_restart_result` currently return `"log"` on False/None branches.

- [ ] **Step 3: Update `should_restart` and `check_restart_result` in `src/orchestrator/nodes.py`**

Find the `should_restart` function and replace it:

```python
def should_restart(state: CrashState) -> str:
    """Conditional edge: restart the container or skip straight to notifications.

    Phase 2b: non-restart analyses now route to notify_slack (restored from
    the Phase 2 workaround that sent them to `log`).
    """
    analysis = state.get("analysis")
    if analysis and analysis.get("restart_likely_fixes"):
        return "attempt_restart"
    return "notify_slack"
```

Find the `check_restart_result` function and replace it:

```python
def check_restart_result(state: CrashState) -> str:
    """Conditional edge: successful restart logs; any other outcome notifies.

    Phase 2b: `restart_success` False or None routes to notify_slack. Only an
    explicit True proceeds to log.
    """
    if state.get("restart_success") is True:
        return "log"
    return "notify_slack"
```

Leave the rest of `nodes.py` (including `notify_slack` / `send_email` stubs) untouched for now — Task 6 replaces them.

- [ ] **Step 4: Update graph mappings in `src/orchestrator/graph.py`**

Find the `workflow.add_conditional_edges("analyze", ...)` block and replace it:

```python
    # Conditional: after analysis, decide restart vs notify.
    workflow.add_conditional_edges(
        "analyze",
        should_restart,
        {"attempt_restart": "restart", "notify_slack": "slack"},
    )
```

Find the `workflow.add_conditional_edges("restart", ...)` block and replace it:

```python
    # Conditional: after restart, success logs; anything else notifies.
    workflow.add_conditional_edges(
        "restart",
        check_restart_result,
        {"log": "log", "notify_slack": "slack"},
    )
```

Leave the `check_multi_crash` conditional edges block exactly as-is.

- [ ] **Step 5: Run test_conditional_edges to verify the 7 tests pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_conditional_edges.py -v`
Expected: PASS (7 tests).

- [ ] **Step 6: Run the full suite — EXPECT the E2E test to fail**

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -10`
Expected: the `test_workflow_end_to_end.py` happy-path test still passes (because its analysis has `restart_likely_fixes=True`, so the flow is still `analyze → restart → log`). But if other workflow tests exist that trigger the False branch, they'll now route to the still-`NotImplementedError` `notify_slack` node and fail. Task 6 and Task 7 fix this.

If ALL tests pass at this step, that's fine too — it means no existing test hits the notify_slack path yet. Task 7 will add new tests that do.

- [ ] **Step 7: Commit**

```bash
git add src/orchestrator/nodes.py src/orchestrator/graph.py tests/unit/orchestrator/test_conditional_edges.py
git commit -m "feat(orchestrator): restore False → notify_slack routing on conditional edges"
```

---

## Task 6: Implement `notify_slack` and `send_email` nodes

**Files:**
- Modify: `src/orchestrator/nodes.py`
- Create: `tests/unit/orchestrator/test_notification_nodes.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/orchestrator/test_notification_nodes.py`:

```python
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
```

The `initial_state` fixture is defined in `tests/unit/orchestrator/conftest.py` (already exists from earlier phases). It already has `tenant_id` and `crash_event` keys — both required here.

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_notification_nodes.py -v`
Expected: FAIL — `notify_slack` and `send_email` currently raise `NotImplementedError`; `SlackAgent` / `EmailAgent` / `get_notification_config` aren't imported into nodes.py yet.

- [ ] **Step 3: Replace `notify_slack` and `send_email` in `src/orchestrator/nodes.py`**

At the top of `src/orchestrator/nodes.py`, add these imports alongside the existing ones (keep existing imports; add only what is missing):

```python
from config.settings import settings
from src.agents.email_agent import EmailAgent
from src.agents.slack_agent import SlackAgent
from src.services.notification_service import get_notification_config
```

Replace the `notify_slack` function:

```python
async def notify_slack(state: CrashState) -> dict:
    """Node: POST a Slack message for the tenant, if configured + enabled."""
    try:
        tenant_id = uuid.UUID(state["tenant_id"])
        config = await get_notification_config(
            async_session_factory, tenant_id, "slack"
        )
        if config is None:
            return {"slack_sent": False}
        webhook_url = (config.config or {}).get("webhook_url")
        if not webhook_url:
            logger.info(
                "Slack config for tenant %s missing webhook_url; skipping",
                tenant_id,
            )
            return {"slack_sent": False}

        agent = SlackAgent(webhook_url=webhook_url)
        sent = await agent.notify(
            state["crash_event"], state.get("analysis") or {}
        )
        return {"slack_sent": sent}
    except Exception:
        logger.exception("notify_slack failed unexpectedly")
        return {"slack_sent": False}
```

Replace the `send_email` function:

```python
async def send_email(state: CrashState) -> dict:
    """Node: send the HTML crash report email for the tenant, if configured."""
    try:
        tenant_id = uuid.UUID(state["tenant_id"])
        config = await get_notification_config(
            async_session_factory, tenant_id, "email"
        )
        if config is None:
            return {"email_sent": False}
        recipient = (config.config or {}).get("to")
        if not recipient:
            logger.info(
                "Email config for tenant %s missing 'to'; skipping",
                tenant_id,
            )
            return {"email_sent": False}

        agent = EmailAgent(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            from_email=settings.smtp_from_email,
        )
        sent = await agent.send(
            state["crash_event"], state.get("analysis") or {}, recipient
        )
        return {"email_sent": sent}
    except Exception:
        logger.exception("send_email failed unexpectedly")
        return {"email_sent": False}
```

Leave `make_call` as `NotImplementedError` — out of scope.

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_notification_nodes.py -v`
Expected: PASS (10 tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `105 passed` (95 + 10).

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/nodes.py tests/unit/orchestrator/test_notification_nodes.py
git commit -m "feat(orchestrator): wire notify_slack and send_email nodes to SlackAgent/EmailAgent"
```

---

## Task 7: Add E2E workflow tests for the notification path

**Files:**
- Modify: `tests/unit/orchestrator/test_workflow_end_to_end.py`

The existing E2E test exercises the `restart_likely_fixes=True` + `restart_success=True` path (analyze → restart → log). Add two new tests for the notification paths, and keep the existing happy-path test as-is.

- [ ] **Step 1: Add two new tests to `test_workflow_end_to_end.py`**

Read the existing `tests/unit/orchestrator/test_workflow_end_to_end.py` to see the existing helper fixtures / imports. Then append these two new tests to the bottom of the file (keeping the existing test intact):

```python
@pytest.mark.asyncio
async def test_workflow_routes_non_restart_analysis_through_notifications(
    initial_state, host_id
):
    """restart_likely_fixes=False → slack → email → log."""
    from src.schemas.crash_event import CrashAnalysis

    non_restart = CrashAnalysis(
        restart_likely_fixes=False,
        root_cause="Port already in use",
        severity="high",
        category="config_error",
        suggestions=["Change port", "Kill other process"],
        confidence=0.88,
    )
    fake_agent = MagicMock()
    fake_agent.analyze = AsyncMock(return_value=(non_restart, False))

    slack_conf = MagicMock()
    slack_conf.is_enabled = True
    slack_conf.config = {"webhook_url": "https://hooks.test/x"}
    email_conf = MagicMock()
    email_conf.is_enabled = True
    email_conf.config = {"to": "dev@test.com"}

    async def fake_get_config(_factory, _tenant_id, channel):
        return slack_conf if channel == "slack" else email_conf

    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    fake_slack = MagicMock()
    fake_slack.notify = AsyncMock(return_value=True)
    fake_email = MagicMock()
    fake_email.send = AsyncMock(return_value=True)

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session), \
         patch("src.orchestrator.nodes.get_fix_agent", return_value=fake_agent), \
         patch("src.orchestrator.nodes.get_notification_config", side_effect=fake_get_config), \
         patch("src.orchestrator.nodes.SlackAgent", return_value=fake_slack), \
         patch("src.orchestrator.nodes.EmailAgent", return_value=fake_email):
        final_state = await crash_workflow.ainvoke(initial_state)

    # analyze ran
    assert final_state["analysis"]["restart_likely_fixes"] is False
    # restart was NOT attempted (routed around)
    assert final_state.get("restart_attempted", False) is False
    # notifications both fired
    fake_slack.notify.assert_awaited_once()
    fake_email.send.assert_awaited_once()
    assert final_state["slack_sent"] is True
    assert final_state["email_sent"] is True


@pytest.mark.asyncio
async def test_workflow_routes_failed_restart_through_notifications(
    initial_state, host_id
):
    """restart_success=False after attempt → slack → email → log."""
    from src.schemas.crash_event import CrashAnalysis

    restart_yes = CrashAnalysis(
        restart_likely_fixes=True,
        root_cause="Transient network blip",
        severity="medium",
        category="network",
        suggestions=["Retry"],
        confidence=0.7,
    )
    fake_agent = MagicMock()
    fake_agent.analyze = AsyncMock(return_value=(restart_yes, False))

    slack_conf = MagicMock()
    slack_conf.is_enabled = True
    slack_conf.config = {"webhook_url": "https://hooks.test/x"}
    email_conf = MagicMock()
    email_conf.is_enabled = True
    email_conf.config = {"to": "dev@test.com"}

    async def fake_get_config(_factory, _tenant_id, channel):
        return slack_conf if channel == "slack" else email_conf

    # Docker client: container.restart raises NotFound → restart_success=False
    import docker.errors
    fake_container = MagicMock()
    fake_container.restart.side_effect = docker.errors.NotFound("gone")
    fake_docker_client = MagicMock()
    fake_docker_client.containers.get.return_value = fake_container

    fake_host = MagicMock()
    fake_host.id = host_id
    fake_host.tcp_url = "tcp://test:2376"
    fake_host.connection_mode = "tcp"
    fake_host.tls_enabled = False
    fake_host.tls_ca = None
    fake_host.tls_cert = None
    fake_host.tls_key = None

    session = AsyncMock()
    session.get = AsyncMock(return_value=fake_host)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    fake_slack = MagicMock()
    fake_slack.notify = AsyncMock(return_value=True)
    fake_email = MagicMock()
    fake_email.send = AsyncMock(return_value=True)

    with patch("src.orchestrator.nodes.async_session_factory", return_value=session), \
         patch("src.orchestrator.nodes.docker.DockerClient", return_value=fake_docker_client), \
         patch("src.orchestrator.nodes.get_fix_agent", return_value=fake_agent), \
         patch("src.orchestrator.nodes.get_notification_config", side_effect=fake_get_config), \
         patch("src.orchestrator.nodes.SlackAgent", return_value=fake_slack), \
         patch("src.orchestrator.nodes.EmailAgent", return_value=fake_email):
        final_state = await crash_workflow.ainvoke(initial_state)

    # restart WAS attempted but failed
    assert final_state["restart_attempted"] is True
    assert final_state["restart_success"] is False
    # notifications both fired
    fake_slack.notify.assert_awaited_once()
    fake_email.send.assert_awaited_once()
    assert final_state["slack_sent"] is True
    assert final_state["email_sent"] is True
```

- [ ] **Step 2: Run the E2E tests to confirm all 3 pass**

Run: `py -3.12 -m pytest tests/unit/orchestrator/test_workflow_end_to_end.py -v`
Expected: PASS (3 tests — existing happy-path + 2 new notification-path tests).

Full suite:

Run: `py -3.12 -m pytest tests/unit/ 2>&1 | tail -3`
Expected: `107 passed` (105 + 2).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/orchestrator/test_workflow_end_to_end.py
git commit -m "test(orchestrator): add E2E tests for notification routing paths"
```

---

## Task 8: Update work tracker

**Files:**
- Modify: `work-tracking/PROGRESS.md`

- [ ] **Step 1: Mark items 8, 9, 12, 13 done**

In `work-tracking/PROGRESS.md`, locate the Phase 2 table. Find these rows:

```markdown
| 8 | `src/agents/slack_agent.py` | Slack webhook notification (Block Kit format) | **High** |
| 9 | `src/agents/email_agent.py` | Email notification (Jinja2 template + SMTP) | **High** |
```

Replace with:

```markdown
| 8 | `src/agents/slack_agent.py` | Slack webhook notification (Block Kit format) | ✅ **Done** |
| 9 | `src/agents/email_agent.py` | Email notification (Jinja2 template + Gmail SMTP via aiosmtplib) | ✅ **Done** |
```

Find these rows:

```markdown
| 12 | `src/orchestrator/nodes.py` → `notify_slack` | Wire Slack agent into orchestrator | **High** |
| 13 | `src/orchestrator/nodes.py` → `send_email` | Wire Email agent into orchestrator | **High** |
```

Replace with:

```markdown
| 12 | `src/orchestrator/nodes.py` → `notify_slack` | Wire Slack agent into orchestrator | ✅ **Done** |
| 13 | `src/orchestrator/nodes.py` → `send_email` | Wire Email agent into orchestrator | ✅ **Done** |
```

- [ ] **Step 2: Add today's daily log entry**

Append to the bottom of the `## Daily Log` section (before the `---` separator that precedes "Quick Reference"):

```markdown
### 2026-04-23 (Continued — notification agents)
- **Status:** ✅ **Phase 2 items #8, #9, #12, #13 shipped.** Slack + Email notifications live. Restored False → notify_slack edges in the orchestrator graph.
- **What was done:**
  - Brainstormed + wrote design spec: `docs/superpowers/specs/2026-04-23-notification-agents-design.md`
  - Wrote 9-task plan: `docs/superpowers/plans/2026-04-23-notification-agents.md`
  - Added `aiosmtplib>=3.0.0` dep; new SMTP settings (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`)
  - `SlackAgent.notify` — httpx POST to per-tenant webhook, Block Kit payload, severity→emoji mapping, truncates to 3 suggestions
  - `EmailAgent.send` — Jinja2 renders `crash_email.html`, aiosmtplib sends over Gmail STARTTLS
  - `get_notification_config(tenant_id, channel)` helper in `notification_service.py` — returns enabled config row or None
  - `notify_slack` / `send_email` orchestrator nodes — per-tenant config lookup, outer exception guard, graph never dies in a notification node
  - Restored `should_restart` False → `notify_slack`; `check_restart_result` non-True → `notify_slack`
  - Updated graph mappings: `{"attempt_restart": "restart", "notify_slack": "slack"}` on `analyze`; `{"log": "log", "notify_slack": "slack"}` on `restart`
  - 31 new unit tests (8 Slack + 6 Email + 5 service helper + 10 node + 2 E2E); 107 tests total
- **Known deferred items:**
  - **CallAgent + Twilio** (item #10) + `make_call` node (#14) — voice escalation. Requires Twilio trial + phone number.
  - **DashboardAgent** (item #11) — separate dashboard-UI concern, not crash-notification.
  - **Retry / backoff** on Slack 429 and SMTP timeouts.
  - **Multi-recipient email** — per-tenant single `to` address only.
  - **Container-owner routing via Docker labels** — listener doesn't capture labels yet.
  - **Rich Slack interactivity** (buttons, threads).
  - **Notification deduplication** — every crash notifies even if Qdrant cache already saw it.
- **Pick up from here:** Good candidates for the next session:
  - **CallAgent + make_call wiring (items #10, #14)** — closes out Phase 2's escalation path. Twilio trial account required.
  - **DashboardAgent (item #11)** + wire into a dashboard API endpoint — useful dashboard UI demo.
  - **Observability & metrics** — populate `llm_provider`/`llm_latency_ms` columns, add Prometheus counters for notification success/failure, tune the Qdrant threshold against real crash data.
  - **Frontend polish** — the Next.js dashboard is already scaffolded; wire it to the API and show live crashes, analyses, and notifications.
```

- [ ] **Step 3: Commit**

```bash
git add work-tracking/PROGRESS.md
git commit -m "docs: mark Phase 2 items 8, 9, 12, 13 complete in work tracker"
```

---

## Task 9: Smoke test — real Slack + real Gmail

**Files:** none — verification only.

User prerequisites:
- In `.env`: `SMTP_USER=<your-gmail@gmail.com>`, `SMTP_PASSWORD=<app-password>`, `SMTP_FROM_EMAIL=<your-gmail@gmail.com>`.
- A Slack incoming webhook URL from any Slack workspace (Slack → Apps → Incoming Webhooks → add one to a channel).

- [ ] **Step 1: Start infra**

Run: `docker compose up -d postgres redis qdrant`
Expected: three services healthy.

- [ ] **Step 2: Run migrations + clean state**

Run:
```bash
py -3.12 -m alembic upgrade head
docker compose exec -T postgres psql -U sentinel -d sentinel -c "TRUNCATE crash_events, notification_configs, docker_hosts, tenants RESTART IDENTITY CASCADE;"
curl -sf -X DELETE http://localhost:6333/collections/crash_history 2>&1 | head -1 || true
```
Expected: migrations up-to-date; truncate succeeds; Qdrant collection deleted or 404.

- [ ] **Step 3: Seed a tenant + docker host**

Run: `PYTHONPATH=. py -3.12 scripts/smoke_seed.py`
Expected: prints `TENANT_ID=<uuid>` and `HOST_ID=<uuid>`. Copy the TENANT_ID — the next step needs it.

- [ ] **Step 4: Seed notification configs**

Write a one-shot script at `scripts/smoke_seed_notifications.py` (new, small utility — commit if you want, else delete after use):

```python
"""Seed NotificationConfig rows for the smoke tenant.

Usage: pass the tenant UUID + Slack webhook + recipient email as env vars:
    SMOKE_TENANT_ID=<uuid> SMOKE_SLACK_WEBHOOK=<url> SMOKE_EMAIL_TO=<addr> \
        PYTHONPATH=. py -3.12 scripts/smoke_seed_notifications.py
"""

import asyncio
import os
import uuid

from src.models.notification_config import NotificationConfig
from src.services.database import async_session_factory


async def seed() -> None:
    tenant_id = uuid.UUID(os.environ["SMOKE_TENANT_ID"])
    webhook = os.environ["SMOKE_SLACK_WEBHOOK"]
    email_to = os.environ["SMOKE_EMAIL_TO"]

    async with async_session_factory() as s:
        s.add(NotificationConfig(
            tenant_id=tenant_id, channel="slack", is_enabled=True,
            use_platform_default=False,
            config={"webhook_url": webhook},
        ))
        s.add(NotificationConfig(
            tenant_id=tenant_id, channel="email", is_enabled=True,
            use_platform_default=False,
            config={"to": email_to},
        ))
        await s.commit()
        print(f"seeded slack+email configs for tenant {tenant_id}")


if __name__ == "__main__":
    asyncio.run(seed())
```

Run (substitute values):
```bash
SMOKE_TENANT_ID=<uuid-from-step-3> \
SMOKE_SLACK_WEBHOOK=<your-webhook-url> \
SMOKE_EMAIL_TO=<your-email@gmail.com> \
PYTHONPATH=. py -3.12 scripts/smoke_seed_notifications.py
```
Expected: `seeded slack+email configs for tenant <uuid>`.

- [ ] **Step 5: Start the worker**

Run (background): `PYTHONPATH=. py -3.12 -u -m src.worker.main`
Expected: worker starts, listener spawns for the seeded host, `docker_hosts.status` transitions to `connected`.

- [ ] **Step 6: Trigger a non-restart crash**

Run: `docker run --name smoke-notify-1 busybox sh -c 'echo "ERROR: port 8080 already in use" >&2; exit 1'`
Expected: container exits with code 1. The LLM will classify as `config_error` with `restart_likely_fixes=False` — routes through `notify_slack → send_email → log`.

Wait ~20 seconds (first-run may include fastembed model download, LLM call, Slack POST, SMTP send).

- [ ] **Step 7: Verify Slack + Email + DB**

Check your Slack channel: a message with the container name, exit code, severity, root cause, and 3 bullet suggestions should appear.

Check your Gmail inbox: an email with subject `[DockerSentinel] Crash: smoke-notify-1` and HTML rendering of the crash report.

Check the DB:
```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "SELECT container_name, LEFT(root_cause, 40) AS root_cause, slack_sent, email_sent, resolved_at IS NOT NULL AS resolved FROM crash_events WHERE container_name='smoke-notify-1';"
```
Expected: one row, `slack_sent=t`, `email_sent=t`, `resolved=t`.

- [ ] **Step 8: Test the is_enabled mute switch**

Disable Slack:
```bash
docker compose exec -T postgres psql -U sentinel -d sentinel -c \
  "UPDATE notification_configs SET is_enabled=false WHERE channel='slack';"
```

Trigger another crash: `docker run --name smoke-notify-2 busybox sh -c 'echo "ERROR: port 8080 already in use" >&2; exit 1'`

Wait ~10 seconds.

Verify:
- No new Slack message appears in the channel.
- Email still arrives in the inbox.
- DB:
  ```bash
  docker compose exec -T postgres psql -U sentinel -d sentinel -c \
    "SELECT container_name, slack_sent, email_sent FROM crash_events WHERE container_name LIKE 'smoke-notify%' ORDER BY created_at;"
  ```
  Expected: two rows. First: `slack_sent=t, email_sent=t`. Second: `slack_sent=f, email_sent=t`.

- [ ] **Step 9: Tear down**

Run:
```bash
docker rm -f smoke-notify-1 smoke-notify-2 2>/dev/null
taskkill //F //IM python.exe 2>&1 | head -3
docker compose down
```

- [ ] **Step 10: Commit the seed helper (optional)**

If you want to keep the notification seed script for future smoke runs:
```bash
git add scripts/smoke_seed_notifications.py
git commit -m "chore: add smoke_seed_notifications helper script"
```

If you'd rather not retain it, delete it and don't commit. Task 9 is otherwise verification-only.

---

## Self-review (completed by the planner)

- **Spec coverage:**
  - SlackAgent.notify with httpx + Block Kit → Task 2.
  - EmailAgent.send with aiosmtplib + Jinja2 → Task 3.
  - `get_notification_config(tenant_id, channel)` helper → Task 4.
  - `notify_slack` + `send_email` orchestrator nodes with outer exception guard → Task 6.
  - `is_enabled` filter respected → Task 4 (SQL clause) + Task 6 (None → skip).
  - Missing webhook_url / missing "to" → skip → Task 6 tests.
  - `should_restart` False → `notify_slack` → Task 5.
  - `check_restart_result` non-True → `notify_slack` → Task 5.
  - Graph edge mappings restored → Task 5.
  - `aiosmtplib` dep + SMTP settings → Task 1.
  - E2E coverage of the notification paths → Task 7.
  - Smoke test acceptance → Task 9.
  - Tracker update → Task 8.
- **Placeholder scan:** No TBD/TODO; every code step is complete code or exact edit instructions.
- **Type/name consistency:**
  - `SlackAgent(webhook_url, timeout_s)` signature matches across Task 2 definition, Task 6 node instantiation, and test assertions.
  - `EmailAgent(host, port, user, password, from_email, timeout_s)` consistent across Task 3 and Task 6.
  - `get_notification_config(session_factory, tenant_id, channel)` signature identical between Task 4 definition, Task 6 callers, and all tests.
  - Return values: `notify_slack` returns `{"slack_sent": bool}`; `send_email` returns `{"email_sent": bool}` — matches state keys used in `log_event` and E2E tests.
  - Conditional edge return values `"attempt_restart"`, `"notify_slack"`, `"log"` consistent between Task 5's function bodies, graph mappings, and test assertions.
- **Known caveat (not a placeholder):** Task 5 will leave the graph in a state where the `notify_slack` edge exists but the node is still `NotImplementedError`. Task 6 immediately fixes this. Running the full suite between Task 5 and Task 6 may show the existing E2E test passing (if `restart_likely_fixes=True`) but any test that triggers the False branch would fail with `NotImplementedError` from the un-replaced notify_slack stub. Tasks 5 and 6 should be run back-to-back.
