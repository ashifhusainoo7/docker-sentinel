import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TenantMixin


class CrashEvent(TenantMixin, Base):
    __tablename__ = "crash_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    docker_host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("docker_hosts.id"), nullable=False, index=True
    )
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    container_id: Mapped[str] = mapped_column(String(64), nullable=False)
    image: Mapped[str] = mapped_column(Text, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    logs: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Analysis results
    root_cause: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))
    severity: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    suggestions: Mapped[dict] = mapped_column(JSONB, default=list)

    # Action tracking
    restart_attempted: Mapped[bool] = mapped_column(Boolean, default=False)
    restart_success: Mapped[bool | None] = mapped_column(Boolean)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    slack_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    call_made: Mapped[bool] = mapped_column(Boolean, default=False)

    # LLM metadata
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    docker_host = relationship("DockerHost", back_populates="crash_events")
