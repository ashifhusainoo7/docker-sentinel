from typing import TypedDict


class CrashState(TypedDict):
    """State that flows through the LangGraph orchestrator."""

    # Input
    tenant_id: str
    crash_event: dict

    # Analysis (populated by Fix Agent)
    analysis: dict | None
    cache_hit: bool

    # Actions taken
    restart_attempted: bool
    restart_success: bool
    slack_sent: bool
    email_sent: bool
    call_triggered: bool

    # Context
    recent_crash_count: int
    docker_host_id: str
