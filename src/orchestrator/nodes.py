from src.orchestrator.state import CrashState


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
    """Node: Attempt to restart the crashed container."""
    raise NotImplementedError(
        "attempt_restart node not yet implemented. "
        "Will use Docker SDK to restart the container, "
        "verify it's running, and update state."
    )


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
