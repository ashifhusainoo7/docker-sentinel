def build_analysis_prompt(crash_event: dict) -> list[dict]:
    """Build the LangChain messages list from a crash event dict.

    Pure function — no side effects, trivially testable.
    """
    container = crash_event.get("container_name") or "<unknown>"
    image = crash_event.get("image") or "<unknown>"
    exit_code = crash_event.get("exit_code")
    event_type = crash_event.get("event_type") or "die"
    logs = crash_event.get("logs") or "<no logs captured>"

    log_lines = logs.splitlines()
    if len(log_lines) > 200:
        log_lines = log_lines[-200:]
    logs_text = "\n".join(log_lines) if log_lines else "<no logs captured>"

    system = (
        "You are a Docker crash analyst. Given a container's crash event and "
        "the last log lines before it exited, produce a structured diagnosis. "
        "Be concise and specific. If the logs are insufficient, set confidence low."
    )
    user = (
        f"Container: {container}\n"
        f"Image: {image}\n"
        f"Exit code: {exit_code}\n"
        f"Event: {event_type}\n\n"
        f"Logs (last 200 lines):\n"
        f"---\n{logs_text}\n---\n\n"
        f"Produce a CrashAnalysis. Set restart_likely_fixes=True only if the "
        f"root cause is transient (OOM, network, dependency startup race). "
        f"Set it to False for config errors, code bugs, or missing dependencies."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
