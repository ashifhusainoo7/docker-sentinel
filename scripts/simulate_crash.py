"""Simulate a Docker container crash for testing the pipeline.

Usage: python scripts/simulate_crash.py --tenant-id <uuid> --host-id <uuid>
"""

import argparse
import asyncio
import uuid

from src.schemas.crash_event import CrashEventCreate
from src.services.redis_stream import publish_crash_event


async def simulate(tenant_id: str, host_id: str):
    event = CrashEventCreate(
        docker_host_id=uuid.UUID(host_id),
        container_name="payment-service",
        container_id="abc123def456",
        image="myorg/payment:latest",
        exit_code=137,
        logs="2026-04-12 10:00:01 ERROR: Out of memory\n"
        "2026-04-12 10:00:01 FATAL: Cannot allocate memory for buffer pool\n"
        "2026-04-12 10:00:01 Container killed by OOM killer",
    )

    message_id = await publish_crash_event(tenant_id, event.model_dump(mode="json"))
    print(f"Crash event published to Redis: {message_id}")
    print(f"Tenant: {tenant_id}")
    print(f"Container: {event.container_name} (exit code {event.exit_code})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a Docker crash event")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--host-id", required=True, help="Docker host UUID")
    args = parser.parse_args()
    asyncio.run(simulate(args.tenant_id, args.host_id))
