import asyncio
import logging
import threading
import time
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
        self._shutdown_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue | None = None
        self._thread: threading.Thread | None = None
        self._consumer_task: asyncio.Task | None = None
        self._async_client = None  # docker client used from the async consumer

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
        if self._thread is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=1000)
        self._async_client = docker.DockerClient(
            base_url=self.host_url, tls=self.tls_config
        )
        self._shutdown_event.clear()
        self._thread = threading.Thread(
            target=self._thread_loop, name=f"docker-monitor-{self.host_id}", daemon=True
        )
        self._thread.start()
        self._consumer_task = asyncio.create_task(self._async_consumer())
        logger.info("Started DockerMonitor for host %s", self.host_id)

    async def stop(self) -> None:
        self._shutdown_event.set()
        self._status = "stopped"
        await update_host_status(
            self._db_session_factory, self.host_id, "stopped", None
        )
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._thread is not None:
            # Thread is daemon; we don't hang on join forever.
            self._thread.join(timeout=5.0)
        if self._async_client is not None:
            try:
                self._async_client.close()
            except Exception:
                pass
        logger.info("Stopped DockerMonitor for host %s", self.host_id)

    def _thread_loop(self) -> None:
        """Runs in a dedicated thread. Bridges docker.events() to the async queue."""
        backoff = 1.0
        while not self._shutdown_event.is_set():
            client = None
            try:
                client = docker.DockerClient(
                    base_url=self.host_url, tls=self.tls_config
                )
                self._set_status("connected", None)
                backoff = 1.0
                for event in client.events(
                    filters={"event": ["die", "oom", "kill"]}, decode=True
                ):
                    if self._shutdown_event.is_set():
                        break
                    if not self._loop or self._loop.is_closed():
                        break
                    asyncio.run_coroutine_threadsafe(
                        self._queue.put(event), self._loop
                    )
            except Exception as exc:
                msg = str(exc)[:255]
                logger.warning(
                    "Docker event stream error on host %s: %s", self.host_id, msg
                )
                self._set_status("reconnecting", msg)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
            finally:
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass

    async def _async_consumer(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._process_event(event, self._async_client)
            except Exception:
                logger.exception("Error processing crash event")

    def _set_status(self, status: str, message: str | None) -> None:
        """Thread-safe status update: schedules coroutine on the main loop."""
        self._status = status
        if self._loop is None or self._loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(
            update_host_status(
                self._db_session_factory, self.host_id, status, message
            ),
            self._loop,
        )
