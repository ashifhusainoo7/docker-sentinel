import asyncio
import logging
import uuid

import docker
import docker.errors

from src.listener._tls import build_tls_config
from src.models.docker_host import DockerHost
from src.orchestrator.state import CrashState
from src.services.database import async_session_factory

logger = logging.getLogger("sentinel.orchestrator")


async def analyze_crash(state: CrashState) -> dict:
    """Node: stub until Fix Agent lands in Phase 2.

    Returns a canned CrashAnalysis dict so the state machine stays live.
    Sets restart_likely_fixes=True to route through attempt_restart → log_event.
    """
    return {
        "analysis": {
            "restart_likely_fixes": True,
            "root_cause": "Pending Fix Agent implementation (Phase 2)",
            "severity": "medium",
            "category": "unknown",
            "suggestions": [
                "Fix Agent not yet implemented — placeholder analysis"
            ],
            "confidence": 0.0,
        },
        "cache_hit": False,
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
        return {"restart_attempted": True, "restart_success": False}

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
    """Node: Send Slack notification."""
    raise NotImplementedError(
        "notify_slack node not yet implemented. "
        "Will look up tenant notification config, "
        "instantiate SlackAgent, and call notify()."
    )


async def send_email(state: CrashState) -> dict:
    """Node: Send detailed email report."""
    raise NotImplementedError(
        "send_email node not yet implemented. "
        "Will look up tenant notification config + container owner, "
        "instantiate EmailAgent, and call send()."
    )


async def make_call(state: CrashState) -> dict:
    """Node: Make voice call for critical multi-crash escalation."""
    raise NotImplementedError(
        "make_call node not yet implemented. "
        "Will look up tenant escalation config, "
        "instantiate CallAgent, and call escalate()."
    )


async def log_event(state: CrashState) -> dict:
    """Node: Log the crash event and all actions to the database."""
    raise NotImplementedError(
        "log_event node not yet implemented. "
        "Will update crash_event record in PostgreSQL with analysis results "
        "and action flags, then update Prometheus metrics."
    )


def should_restart(state: CrashState) -> str:
    """Conditional edge: decide whether to attempt restart or go straight to notification."""
    analysis = state.get("analysis")
    if analysis and analysis.get("restart_likely_fixes"):
        return "attempt_restart"
    return "notify_slack"


def check_restart_result(state: CrashState) -> str:
    """Conditional edge: after restart, check if it succeeded."""
    if state.get("restart_success"):
        return "log"
    return "notify_slack"


def check_multi_crash(state: CrashState) -> str:
    """Conditional edge: after email, check if multi-crash threshold is met."""
    if state.get("recent_crash_count", 0) >= 2:
        return "make_call"
    return "log"
