# Notification Agents (Phase 2) — Slack + Email — Design

**Date:** 2026-04-23
**Scope:** Phase 2 items #8, #9, #12, #13 from `work-tracking/PROGRESS.md` — build `SlackAgent` and `EmailAgent`, wire them into the orchestrator (`notify_slack` and `send_email` nodes), and restore the `False → notify_slack` graph edges that Phase 2 stubbed out.

Out of scope:
- `CallAgent` / Twilio (item #10) — remains `NotImplementedError`.
- `DashboardAgent` (item #11) — separate concern (UI AI summary), not crash-notification flow.
- `make_call` node (item #14) — `check_multi_crash` continues to route to `log` until Twilio lands.
- Retry / backoff on transient delivery failures.
- Notification-level deduplication (we notify every crash; Qdrant cache reduces LLM cost only).
- Container-owner email routing via Docker labels.

## Goals

1. When a crash is analyzed as *not restart-fixable* (e.g., config error, code bug), a Slack message and email notification are delivered to the tenant's configured channel(s).
2. When a restart is attempted and fails, the same Slack + email path runs.
3. `NotificationConfig.is_enabled` respected — disabled channels silently skip.
4. Missing or misconfigured channel (no webhook URL / no "to" address) silently skips — no workflow crash.
5. All delivery failures (network, auth, timeout, rate limit) produce `*_sent=False` in state and DB, never an exception past the node boundary.
6. Graph has no `NotImplementedError` nodes on the default flows after this session.

## Non-goals

- Retry / exponential backoff.
- Per-user email (only per-tenant `to` address today).
- Rich interactive Slack messages (buttons, threads).
- SPF/DKIM/DMARC setup or email deliverability tuning beyond Gmail SMTP.
- Twilio voice calls.

## Architecture

### Graph edge changes

Before (Phase 2 end state):

```
analyze → should_restart → {True: restart, False: log}
restart → check_restart_result → {True: log}              [always "log"]
```

After (this session):

```
analyze → should_restart → {True: restart, False: slack}
restart → check_restart_result → {True: log, False: slack}
slack → email (always)
email → check_multi_crash → {log}                         [still "log"; call is NotImplemented]
```

### End-to-end flow for a non-restart crash

```
event → _process_event → workflow.ainvoke
         ↓
    analyze_crash (FixAgent)                   Qdrant cache check → LLM
         ↓ analysis with restart_likely_fixes=False
    should_restart returns "notify_slack"
         ↓
    notify_slack node
         ├── get_notification_config(tenant, "slack")
         │   ├── None → return {slack_sent: False}
         │   └── Row  → continue
         ├── webhook_url = config.config.get("webhook_url")
         │   ├── missing → log INFO, return {slack_sent: False}
         │   └── present → continue
         └── SlackAgent(webhook_url).notify(event, analysis)
             ├── POST Block Kit → returns True on 2xx
             └── any error → logs + returns False
         ↓ {slack_sent: True|False}
    send_email node                              (same shape, targets recipient)
         ├── get_notification_config(tenant, "email")
         ├── recipient = config.config.get("to")
         └── EmailAgent(gmail_smtp).send(event, analysis, recipient)
         ↓ {email_sent: True|False}
    check_multi_crash returns "log"
         ↓
    log_event persists slack_sent + email_sent + resolved_at
```

## Key design decisions

### Per-tenant config, no platform default

Slack webhook and email recipient both come from `NotificationConfig.config` JSONB per tenant. No env-var fallback. Tenants that don't seed a config row silently skip the respective channel.

**Why:** Matches how a real multi-tenant SaaS works — each tenant brings its own Slack workspace and distribution list. Portfolio demo is a one-time DB insert for the smoke tenant.

### Gmail SMTP over `aiosmtplib`, not SendGrid

New settings: `smtp_host` (default `"smtp.gmail.com"`), `smtp_port` (`587`), `smtp_user`, `smtp_password`. `smtp_from_email` already exists. User supplies Gmail address + app password directly in `.env`; code reads via `settings.smtp_*`.

**Why:** No third-party signup, emails land in real inboxes, Gmail's 500/day limit is ample for portfolio + demos. `aiosmtplib` is the canonical async SMTP library. Gmail app passwords are stable and don't require domain verification.

### `is_enabled=False` mutes the channel

`get_notification_config` filters by `is_enabled == True`. Operator can disable per tenant without deleting the row (DB shape already has this flag — we use it).

### Per-node exception guard

Each node wraps its body in `try/except Exception` → returns `{channel_sent: False}` + `logger.exception`. The graph never dies inside a notification node even if DB is down.

### `log_event` doesn't change

Already reads `state.get("slack_sent", False)` and `state.get("email_sent", False)` in its UPDATE. No code change needed.

## Component specifications

### `SlackAgent` (`src/agents/slack_agent.py` — full rewrite)

```python
import logging
from typing import Any

import httpx

logger = logging.getLogger("sentinel.agents.slack")


class SlackAgent:
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

### `EmailAgent` (`src/agents/email_agent.py` — full rewrite)

```python
import logging
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings

logger = logging.getLogger("sentinel.agents.email")


class EmailAgent:
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

### Notification config helper (`src/services/notification_service.py` — add function)

```python
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

### Orchestrator nodes (`src/orchestrator/nodes.py`)

Replace `notify_slack`:

```python
async def notify_slack(state: CrashState) -> dict:
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

Replace `send_email`:

```python
async def send_email(state: CrashState) -> dict:
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

Restore `should_restart` + `check_restart_result`:

```python
def should_restart(state: CrashState) -> str:
    analysis = state.get("analysis")
    if analysis and analysis.get("restart_likely_fixes"):
        return "attempt_restart"
    return "notify_slack"


def check_restart_result(state: CrashState) -> str:
    if state.get("restart_success") is True:
        return "log"
    return "notify_slack"
```

### Graph rewiring (`src/orchestrator/graph.py`)

```python
workflow.add_conditional_edges(
    "analyze",
    should_restart,
    {"attempt_restart": "restart", "notify_slack": "slack"},
)

workflow.add_conditional_edges(
    "restart",
    check_restart_result,
    {"log": "log", "notify_slack": "slack"},
)
```

`check_multi_crash` is untouched: its existing graph mapping `{"make_call": "call", "log": "log"}` stays in place. Since `state["recent_crash_count"]` is always `0` in the current state-building code (see `worker/_process_event`), `check_multi_crash` always returns `"log"` in practice today — `"make_call"` / the `call` node never fires. `call` stays `NotImplementedError` until the future CallAgent session.

### Settings (`config/settings.py`)

Add:

```python
smtp_host: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_user: str = ""
smtp_password: str = ""
# smtp_from_email already exists at line 42
```

## Error handling

| Failure | Where | Response |
|---|---|---|
| NotificationConfig row missing | `get_notification_config` | Returns None → node returns `{*_sent: False}`. |
| Row exists but `is_enabled=False` | SQL filter | Returns None → skip. |
| Row exists but `config` missing key | Node check | Log INFO, return `False`. |
| Slack non-2xx response (404, 429, 500) | `SlackAgent.notify` | Log WARNING, return False. |
| Slack network error | `httpx` exception | Log EXCEPTION, return False. |
| SMTP auth failure | `aiosmtplib.send` | Log EXCEPTION, return False. |
| SMTP host unreachable | `aiosmtplib.send` | Log EXCEPTION, return False. |
| SMTP send timeout | `timeout=15s` | TimeoutError caught, return False. |
| Jinja2 render error | `EmailAgent.send` | Log EXCEPTION, return False. (Template is static; would need a code bug.) |
| DB error inside `get_notification_config` | session_factory raises | Caught by outer node try/except → return False, workflow survives. |

## Configuration

### New settings
- `smtp_host: str = "smtp.gmail.com"`
- `smtp_port: int = 587`
- `smtp_user: str = ""`
- `smtp_password: str = ""`

### Unchanged
- `smtp_from_email: str = ""` — already in settings.

### User action needed before smoke test
- Add `SMTP_USER` (your Gmail) and `SMTP_PASSWORD` (Gmail app password) to `.env`.
- Add `SMTP_FROM_EMAIL` to `.env` (usually same as `SMTP_USER` for Gmail).

## Dependencies

Add to `pyproject.toml`:

```
aiosmtplib>=3.0.0
```

Already present: `httpx>=0.27.0`, `jinja2>=3.1.0`, `sqlalchemy[asyncio]>=2.0.30`.

## Testing

### Unit tests

**`tests/unit/agents/test_slack_agent.py`** (~8 tests):
- POST to webhook URL.
- Returns True on 2xx.
- Returns False on 4xx, 5xx.
- Swallows network errors.
- Block Kit payload contains all crash fields.
- Truncates suggestions to 3.
- Severity→emoji mapping.

**`tests/unit/agents/test_email_agent.py`** (~6 tests):
- Renders template with event/analysis data.
- Sets subject from container_name.
- Returns True on successful send.
- Returns False on SMTP error.
- Returns False on timeout.
- Uses Gmail defaults (host/port/starttls).

**`tests/unit/services/test_notification_service.py`** (~5 tests):
- Returns row when enabled.
- Returns None when disabled.
- Returns None when missing.
- Channel filter works (slack vs email).
- Tenant filter works.

**`tests/unit/orchestrator/test_notification_nodes.py`** (~10 tests):

`notify_slack`:
- Skips when no config.
- Skips when webhook_url missing.
- Calls agent when config valid; passes crash_event + analysis.
- Returns False on agent failure.
- Catches unexpected exceptions.

`send_email`:
- Mirror set of 5.

**`tests/unit/orchestrator/test_workflow_end_to_end.py`** (updates + 2 new):
- Existing happy path (cache hit → restart → log) still passes.
- NEW: `restart_likely_fixes=False` routes through slack → email → log; both `*_sent` assertions hold.
- NEW: `restart_success=False` routes through slack → email → log.

### No real-delivery tests in CI

All Slack/SMTP interactions mocked. No network calls in CI.

### Expected counts

- +8 Slack
- +6 Email
- +5 notification_service
- +10 orchestrator nodes
- +2 workflow E2E
- = ~31 new tests

Current: 76 unit tests. After: ~107.

### Smoke test — real delivery

User provides in `.env`: `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`.
User provides a Slack incoming webhook URL (via Slack app in their workspace).

Steps:
1. `docker compose up -d postgres redis qdrant`
2. Run migrations + seed tenant + Docker host.
3. Seed two `NotificationConfig` rows:
   ```python
   NotificationConfig(tenant_id=..., channel="slack", is_enabled=True,
                      config={"webhook_url": "<user webhook>"})
   NotificationConfig(tenant_id=..., channel="email", is_enabled=True,
                      config={"to": "<user email>"})
   ```
4. Start worker.
5. Trigger port-conflict crash (LLM → `restart_likely_fixes=False`):
   ```bash
   docker run --name smoke-phase2b busybox sh -c 'echo "ERROR: port 8080 in use" >&2; exit 1'
   ```
6. Verify:
   - Slack message appears in the user's channel.
   - Email arrives in the user's Gmail inbox (HTML rendered).
   - `crash_events` row: `slack_sent=t`, `email_sent=t`, `resolved_at IS NOT NULL`.
7. `UPDATE notification_configs SET is_enabled=false WHERE channel='slack'` → trigger another crash → Slack silent, email still delivered.

## Acceptance criteria

1. A non-restart crash produces a Slack message in the user's channel (verified via smoke test).
2. Same crash produces an email in the user's Gmail inbox (HTML, rendered from `crash_email.html`).
3. `slack_sent` and `email_sent` flags in `crash_events` table match reality.
4. Disabling `NotificationConfig.is_enabled` silently skips that channel; workflow completes normally.
5. Missing `NotificationConfig` row for a channel silently skips; workflow completes.
6. Slack webhook failure / SMTP failure does not crash the workflow.
7. All unit tests pass with mocked delivery.
8. Graph has zero `NotImplementedError` on the default flows (`call` remains unimplemented but is no longer on a default path).

## Deferred items

- **CallAgent + make_call wiring** (items #10, #14) — Twilio setup requires trial account + phone number. Dedicated session.
- **DashboardAgent** (item #11) — separate dashboard-UI concern.
- **Retry / backoff** on Slack 429 and SMTP timeouts.
- **Multi-user email broadcast** — per-tenant `to` only today.
- **Container-owner routing via Docker labels** — listener doesn't capture labels today.
- **Rich Slack interactions** (buttons, threads, action_ids).
- **Notification deduplication** — every crash notifies even if semantically cached.
- **Email attachments** (e.g., full log file).
- **Domain verification for email** — Gmail SMTP doesn't need it.
