import uuid
from datetime import datetime, timezone

from src.schemas.crash_event import CrashEventCreate


def test_crash_event_create_accepts_event_type_and_timestamp():
    payload = CrashEventCreate(
        docker_host_id=uuid.uuid4(),
        container_name="web-1",
        container_id="abc123",
        image="nginx:latest",
        exit_code=137,
        logs="oom",
        event_type="die",
        event_timestamp=datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert payload.event_type == "die"
    assert payload.event_timestamp.isoformat() == "2026-04-21T12:00:00+00:00"


def test_crash_event_create_without_new_fields_still_valid():
    payload = CrashEventCreate(
        docker_host_id=uuid.uuid4(),
        container_name="web-1",
        container_id="abc123",
        image="nginx:latest",
    )
    assert payload.event_type is None
    assert payload.event_timestamp is None
