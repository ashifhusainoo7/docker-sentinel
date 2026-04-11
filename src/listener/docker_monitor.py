import logging

logger = logging.getLogger("sentinel.listener")


class DockerMonitor:
    """Connects to a remote Docker daemon and listens for crash events.

    Uses Docker SDK for Python over TCP/TLS.
    Captures 'die', 'oom', 'kill' events and pulls last 200 log lines.
    """

    def __init__(self, host_url: str, tls_config: dict | None = None):
        self.host_url = host_url
        self.tls_config = tls_config
        self._running = False

    async def start(self) -> None:
        """Start listening for Docker events on the remote daemon."""
        raise NotImplementedError(
            "Docker event listener not yet implemented. "
            "Will use docker.DockerClient(base_url=host_url) to connect, "
            "then client.events(filters={'event': ['die', 'oom', 'kill']}) "
            "to stream events. Each event triggers CrashEvent creation."
        )

    async def stop(self) -> None:
        """Stop listening and disconnect."""
        self._running = False
        logger.info("Stopped monitoring %s", self.host_url)
