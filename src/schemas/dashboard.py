from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    ai_summary: str
    total_crashes_24h: int
    total_restarts_24h: int
    active_containers: int
    cache_hit_rate: float


class MetricsResponse(BaseModel):
    mttr_seconds: float | None
    cache_hit_rate: float
    restart_success_rate: float
    crashes_per_hour: float
    top_category: str | None


class TimelinePoint(BaseModel):
    timestamp: datetime
    crash_count: int


class TimelineResponse(BaseModel):
    points: list[TimelinePoint]
    period: str  # '24h' | '7d' | '30d'
