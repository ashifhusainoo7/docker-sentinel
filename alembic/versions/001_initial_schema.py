"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2026-04-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("oauth_provider", sa.String(50)),
        sa.Column("oauth_provider_id", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "docker_hosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connection_mode", sa.String(20), nullable=False),
        sa.Column("tcp_url", sa.Text()),
        sa.Column("tls_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("tls_ca", sa.Text()),
        sa.Column("tls_cert", sa.Text()),
        sa.Column("tls_key", sa.Text()),
        sa.Column("agent_id", sa.String(255)),
        sa.Column("agent_last_seen", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("monitor_all_containers", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("container_filter", postgresql.JSONB(), server_default="[]"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("status_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "crash_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("docker_host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("docker_hosts.id"), nullable=False, index=True),
        sa.Column("container_name", sa.String(255), nullable=False),
        sa.Column("container_id", sa.String(64), nullable=False),
        sa.Column("image", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("logs", sa.Text()),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("root_cause", sa.Text()),
        sa.Column("category", sa.String(50)),
        sa.Column("severity", sa.String(20)),
        sa.Column("confidence", sa.Float()),
        sa.Column("suggestions", postgresql.JSONB(), server_default="[]"),
        sa.Column("restart_attempted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("restart_success", sa.Boolean()),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("slack_sent", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("email_sent", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("call_made", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("llm_latency_ms", sa.Integer()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notification_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("use_platform_default", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "channel"),
    )

    op.create_table(
        "escalation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("escalation_rules")
    op.drop_table("notification_configs")
    op.drop_table("crash_events")
    op.drop_table("docker_hosts")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("tenants")
