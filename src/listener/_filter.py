def should_monitor(
    container_name: str, monitor_all: bool, whitelist: list[str]
) -> bool:
    """Return True if a container should produce crash events.

    Exact string match against the whitelist. Glob/regex is out of scope.
    """
    if monitor_all:
        return True
    return container_name in whitelist
