from typing import TypedDict


class CrashState(TypedDict):
    """State that flows through the LangGraph orchestrator."""

    # Input — set by worker._process_event before invocation
    tenant_id: str
    crash_event_id: str
    docker_host_id: str
    crash_event: dict

    # Populated by analyze_crash (stub today, Fix Agent in Phase 2)
    analysis: dict | None
    cache_hit: bool

    # Populated by attempt_restart
    restart_attempted: bool
    restart_success: bool | None

    # Populated by notification nodes (NotImplementedError for Phase 1)
    slack_sent: bool
    email_sent: bool
    call_triggered: bool

    # Stretch — 0 for Phase 1
    recent_crash_count: int
