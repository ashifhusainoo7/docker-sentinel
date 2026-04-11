import logging

logger = logging.getLogger("sentinel.listener.manager")


class ListenerManager:
    """Manages Docker listeners across all tenants and hosts.

    Polls PostgreSQL for active docker_hosts records.
    Spawns/stops async listeners as hosts are added/removed.
    Handles reconnection on failure.
    """

    def __init__(self):
        self._listeners: dict[str, object] = {}  # host_id -> DockerMonitor

    async def sync_listeners(self) -> None:
        """Poll DB for active hosts and sync listener state.

        - New hosts: spawn listener
        - Removed/deactivated hosts: stop listener
        - Failed listeners: attempt reconnection
        """
        raise NotImplementedError(
            "Listener sync not yet implemented. "
            "Will query docker_hosts for active TCP hosts, "
            "compare with running listeners, and spawn/stop as needed."
        )

    async def start(self) -> None:
        """Start the listener manager loop."""
        raise NotImplementedError(
            "Listener manager start not yet implemented. "
            "Will run sync_listeners() on a polling interval (e.g., every 30s)."
        )

    async def stop(self) -> None:
        """Stop all listeners gracefully."""
        for host_id, listener in self._listeners.items():
            logger.info("Stopping listener for host %s", host_id)
        self._listeners.clear()
