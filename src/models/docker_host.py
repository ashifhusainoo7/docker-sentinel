import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TenantMixin, TimestampMixin


class DockerHost(TenantMixin, TimestampMixin, Base):
    __tablename__ = "docker_hosts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_mode: Mapped[str] = mapped_column(String(20), nullable=False)

    # TCP mode fields
    tcp_url: Mapped[str | None] = mapped_column(Text)
    tls_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tls_ca: Mapped[str | None] = mapped_column(Text)
    tls_cert: Mapped[str | None] = mapped_column(Text)
    tls_key: Mapped[str | None] = mapped_column(Text)

    # Agent mode fields
    agent_id: Mapped[str | None] = mapped_column(String(255))
    agent_last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Monitoring config
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_all_containers: Mapped[bool] = mapped_column(Boolean, default=True)
    container_filter: Mapped[dict] = mapped_column(JSONB, default=list)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    status_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    tenant = relationship("Tenant", back_populates="docker_hosts")
    crash_events = relationship("CrashEvent", back_populates="docker_host", lazy="selectin")
