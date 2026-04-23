import asyncio
import logging
import uuid

import docker
import docker.errors
from sqlalchemy import func, update

from config.settings import settings
from src.agents.email_agent import EmailAgent
from src.agents.fix_agent import get_fix_agent
from src.agents.slack_agent import SlackAgent
from src.listener._tls import build_tls_config
from src.models.crash_event import CrashEvent
from src.models.docker_host import DockerHost
from src.orchestrator.state import CrashState
from src.services.database import async_session_factory
from src.services.notification_service import get_notification_config

logger = logging.getLogger("sentinel.orchestrator")


async def analyze_crash(state: CrashState) -> dict:
    """Node: call FixAgent to analyze the crash event.

    Phase 3: tenant_id threaded through to CrashMemory for multi-tenant
    cache isolation.
    """
    agent = get_fix_agent()
    analysis, cache_hit = await agent.analyze(
        state["crash_event"], state["tenant_id"]
    )
    return {
        "analysis": analysis.model_dump(),
        "cache_hit": cache_hit,
    }


async def attempt_restart(state: CrashState) -> dict:
    """Node: attempt container restart on its Docker host.

    Stateless — builds a fresh Docker client per invocation.
    """
    host_id = uuid.UUID(state["docker_host_id"])
    container_id = state["crash_event"]["container_id"]

    async with async_session_factory() as session:
        host = await session.get(DockerHost, host_id)

    if host is None:
        logger.warning("Docker host %s not found; cannot restart", host_id)
        return {"restart_attempted": False, "restart_success": None}

    if host.connection_mode != "tcp" or not host.tcp_url:
        logger.warning(
            "Host %s is not TCP-mode (mode=%s); skipping restart",
            host_id,
            host.connection_mode,
        )
        return {"restart_attempted": False, "restart_success": None}

    tls_config = build_tls_config(host)

    def _do_restart() -> bool:
        client = docker.DockerClient(base_url=host.tcp_url, tls=tls_config)
        try:
            container = client.containers.get(container_id)
            container.restart(timeout=10)
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError:
            logger.exception(
                "Restart failed for container %s on host %s",
                container_id,
                host_id,
            )
            return False
        finally:
            try:
                client.close()
            except Exception:
                pass

    success = await asyncio.to_thread(_do_restart)
    return {"restart_attempted": True, "restart_success": success}


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


async def make_call(state: CrashState) -> dict:
    """Node: voice-call escalation for multi-crash scenarios.

    Phase 2b: CallAgent is not yet implemented. The graph can reach this
    node only when state["recent_crash_count"] >= 2, which the worker
    currently never sets (always 0 in _process_event). The no-op return
    below is defensive — it keeps the workflow alive if someone later
    starts populating recent_crash_count before CallAgent lands.
    """
    logger.info(
        "make_call reached but CallAgent not yet implemented; skipping"
    )
    return {"call_triggered": False}


async def log_event(state: CrashState) -> dict:
    """Node: UPDATE the pending CrashEvent row with analysis + action results.

    Sets resolved_at = now() unconditionally — "workflow completed",
    not "problem fixed".
    """
    crash_id = uuid.UUID(state["crash_event_id"])
    analysis = state.get("analysis") or {}

    async with async_session_factory() as session:
        await session.execute(
            update(CrashEvent)
            .where(CrashEvent.id == crash_id)
            .values(
                root_cause=analysis.get("root_cause"),
                category=analysis.get("category"),
                severity=analysis.get("severity"),
                confidence=analysis.get("confidence"),
                suggestions=analysis.get("suggestions") or [],
                restart_attempted=state.get("restart_attempted", False),
                restart_success=state.get("restart_success"),
                cache_hit=state.get("cache_hit", False),
                slack_sent=state.get("slack_sent", False),
                email_sent=state.get("email_sent", False),
                call_made=state.get("call_triggered", False),
                resolved_at=func.now(),
            )
        )
        await session.commit()
    return {}


def should_restart(state: CrashState) -> str:
    """Conditional edge: restart the container or skip straight to notifications.

    Phase 2b: non-restart analyses now route to notify_slack (restored from
    the Phase 2 workaround that sent them to `log`).
    """
    analysis = state.get("analysis")
    if analysis and analysis.get("restart_likely_fixes"):
        return "attempt_restart"
    return "notify_slack"


def check_restart_result(state: CrashState) -> str:
    """Conditional edge: successful restart logs; any other outcome notifies.

    Phase 2b: `restart_success` False or None routes to notify_slack. Only an
    explicit True proceeds to log.
    """
    if state.get("restart_success") is True:
        return "log"
    return "notify_slack"


def check_multi_crash(state: CrashState) -> str:
    """Conditional edge: after email, check if multi-crash threshold is met."""
    if state.get("recent_crash_count", 0) >= 2:
        return "make_call"
    return "log"
