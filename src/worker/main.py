import asyncio
import logging
import signal

from src.listener.manager import ListenerManager
from src.services.metrics import start_metrics_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("sentinel.worker")


async def consume_crash_events():
    """Main loop: consume crash events from Redis and run through LangGraph orchestrator."""
    raise NotImplementedError(
        "Crash event consumer not yet implemented. "
        "Will poll all tenant Redis streams, deserialize CrashEvents, "
        "run each through crash_workflow.ainvoke(), and handle results."
    )


async def main():
    logger.info("Starting DockerSentinel Worker...")

    # Start Prometheus metrics server for worker
    start_metrics_server(port=9091)

    # Start listener manager (manages Docker connections)
    manager = ListenerManager()

    # Handle shutdown gracefully
    shutdown_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

    logger.info("Worker ready. Waiting for crash events...")

    # Placeholder — will run:
    # await asyncio.gather(
    #     manager.start(),
    #     consume_crash_events(),
    # )

    await shutdown_event.wait()
    await manager.stop()
    logger.info("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
