import asyncio
import logging
import uuid
from datetime import datetime, timezone

import docker
import docker.errors

from src.listener._dedup import DedupCache
from src.listener._filter import should_monitor
from src.listener._status import update_host_status
from src.services.redis_stream import publish_crash_event

logger = logging.getLogger("sentinel.listener")


class DockerMonitor:
    """Connects to a remote Docker daemon and listens for crash events.

    A worker thread runs the blocking docker.events() generator and pushes
    each event onto an asyncio.Queue. An async consumer drains the queue,
    applies filter + dedup, fetches logs, and publishes to Redis.
    """

    def __init__(
        self,
        host_id: uuid.UUID,
        tenant_id: uuid.UUID,
        host_url: str,
        tls_config,
        monitor_all_containers: bool,
        container_filter: list[str],
        db_session_factory,
    ):
        self.host_id = host_id
        self.tenant_id = tenant_id
        self.host_url = host_url
        self.tls_config = tls_config
        self.monitor_all_containers = monitor_all_containers
        self.container_filter = list(container_filter or [])
        self._db_session_factory = db_session_factory
        self._dedup = DedupCache(window_seconds=60.0)
        self._status = "pending"

    @property
    def status(self) -> str:
        return self._status

    async def _process_event(self, event: dict, client) -> None:
        attrs = event.get("Actor", {}).get("Attributes", {})
        container_id = event.get("id") or event.get("Actor", {}).get("ID", "")
        container_name = attrs.get("name", "")
        image = attrs.get("image", "")
        exit_code_raw = attrs.get("exitCode")
        exit_code = int(exit_code_raw) if exit_code_raw not in (None, "") else None
        event_type = event.get("Action", "")
        event_ts_raw = event.get("time")
        event_ts = (
            datetime.fromtimestamp(event_ts_raw, tz=timezone.utc)
            if event_ts_raw
            else datetime.now(tz=timezone.utc)
        )

        if not should_monitor(
            container_name, self.monitor_all_containers, self.container_filter
        ):
            return

        if self._dedup.is_duplicate(str(self.host_id), container_id):
            logger.debug(
                "Deduped crash event for host=%s container=%s",
                self.host_id,
                container_id,
            )
            return

        logs = await self._fetch_logs(client, container_id)

        payload = {
            "docker_host_id": str(self.host_id),
            "container_name": container_name,
            "container_id": container_id,
            "image": image,
            "exit_code": exit_code,
            "logs": logs,
            "event_type": event_type,
            "event_timestamp": event_ts.isoformat(),
        }
        await publish_crash_event(str(self.tenant_id), payload)
        logger.info(
            "Published crash event host=%s container=%s event=%s",
            self.host_id,
            container_name,
            event_type,
        )

    async def _fetch_logs(self, client, container_id: str) -> str | None:
        def _get():
            try:
                container = client.containers.get(container_id)
                return container.logs(tail=200).decode("utf-8", errors="replace")
            except docker.errors.NotFound:
                return None

        return await asyncio.to_thread(_get)

    async def start(self) -> None:
        raise NotImplementedError("Implemented in Task 7")

    async def stop(self) -> None:
        raise NotImplementedError("Implemented in Task 7")
