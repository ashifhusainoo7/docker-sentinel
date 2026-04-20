import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CrashAnalysis(BaseModel):
    """Structured output from the Fix Agent — matches design doc exactly."""

    restart_likely_fixes: bool = Field(
        description="True if restart will likely resolve the issue"
    )
    root_cause: str = Field(description="One-line root cause summary")
    severity: str = Field(description="critical/high/medium/low")
    category: str = Field(
        description="oom | dependency_failure | config_error | code_bug | network | unknown"
    )
    suggestions: list[str] = Field(
        description="Ordered fix suggestions, most impactful first"
    )
    confidence: float = Field(description="0.0 to 1.0")


class CrashEventCreate(BaseModel):
    """Used internally when creating a crash event from Docker listener."""

    docker_host_id: uuid.UUID
    container_name: str
    container_id: str
    image: str
    exit_code: int | None = None
    logs: str | None = None
    event_type: str | None = None
    event_timestamp: datetime | None = None


class CrashEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    docker_host_id: uuid.UUID
    container_name: str
    container_id: str
    image: str
    exit_code: int | None
    logs: str | None
    timestamp: datetime
    root_cause: str | None
    category: str | None
    severity: str | None
    confidence: float | None
    suggestions: list
    restart_attempted: bool
    restart_success: bool | None
    cache_hit: bool
    slack_sent: bool
    email_sent: bool
    call_made: bool
    llm_provider: str | None
    llm_latency_ms: int | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrashStats(BaseModel):
    total_crashes: int
    crashes_today: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    cache_hit_rate: float
    avg_resolution_time_ms: float | None


class TopCrasher(BaseModel):
    container_name: str
    crash_count: int
    last_crash: datetime
