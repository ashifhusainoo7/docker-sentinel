from langgraph.graph import END, StateGraph

from src.orchestrator.nodes import (
    analyze_crash,
    attempt_restart,
    check_multi_crash,
    check_restart_result,
    log_event,
    make_call,
    notify_slack,
    send_email,
    should_restart,
)
from src.orchestrator.state import CrashState


def build_crash_workflow() -> StateGraph:
    """Build the LangGraph state machine for crash event processing.

    Decision Flow:
        ANALYZE → restart_likely? → RESTART → success? → LOG
                                                       → SLACK → EMAIL → multi_crash? → CALL → LOG
                → code/config issue → SLACK → EMAIL → multi_crash? → CALL → LOG
                                                                    → LOG
    """
    workflow = StateGraph(CrashState)

    # Add nodes
    workflow.add_node("analyze", analyze_crash)
    workflow.add_node("restart", attempt_restart)
    workflow.add_node("slack", notify_slack)
    workflow.add_node("email", send_email)
    workflow.add_node("call", make_call)
    workflow.add_node("log", log_event)

    # Entry point
    workflow.set_entry_point("analyze")

    # Conditional: after analysis, decide restart vs skip to log.
    # Phase 2: notify_slack stubbed, so `log` branch is the not-restart path.
    # Phase 2.5: restore "notify_slack" → "slack" when notifications land.
    workflow.add_conditional_edges(
        "analyze",
        should_restart,
        {"attempt_restart": "restart", "log": "log"},
    )

    # Conditional: after restart, route to log.
    # Phase 2: notify_slack stubbed. Phase 2.5 will add a "notify_slack" → "slack"
    # entry here once check_restart_result returns it for restart_success=False.
    workflow.add_conditional_edges(
        "restart",
        check_restart_result,
        {"log": "log"},
    )

    # Slack always flows to email
    workflow.add_edge("slack", "email")

    # Conditional: after email, check multi-crash threshold
    workflow.add_conditional_edges(
        "email",
        check_multi_crash,
        {"make_call": "call", "log": "log"},
    )

    # Call flows to log
    workflow.add_edge("call", "log")

    # Log is the terminal node
    workflow.add_edge("log", END)

    return workflow


# Compile the workflow for use
crash_workflow = build_crash_workflow().compile()
