from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    crashes_24h: int
    restarts_24h: int
    cache_hit_rate: float
    active_hosts: int


class TimelinePoint(BaseModel):
    t: str  # ISO8601 string
    crashes: int
    restarts: int


class DashboardMetrics(BaseModel):
    period: str
    mttr_seconds: float | None
    mttr_delta_pct: float | None
    crashes_total: int
    crashes_delta_pct: float | None
    severity_breakdown: dict[str, int]
    category_breakdown: dict[str, int]


class DashboardTimeline(BaseModel):
    period: str
    bucket: str
    points: list[TimelinePoint]


# Legacy aliases kept for any existing imports (will be replaced by router update)
class MetricsResponse(BaseModel):
    mttr_seconds: float | None
    cache_hit_rate: float
    restart_success_rate: float
    crashes_per_hour: float
    top_category: str | None


class TimelineResponse(BaseModel):
    points: list[TimelinePoint]
    period: str  # '24h' | '7d' | '30d'
