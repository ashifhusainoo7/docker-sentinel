import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification_config import NotificationConfig
from src.schemas.notification import NotificationConfigUpdate


async def get_notification_configs(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[NotificationConfig]:
    result = await db.execute(
        select(NotificationConfig).where(NotificationConfig.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def upsert_notification_config(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    channel: str,
    data: NotificationConfigUpdate,
) -> NotificationConfig:
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.tenant_id == tenant_id,
            NotificationConfig.channel == channel,
        )
    )
    config = result.scalar_one_or_none()

    if config:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
    else:
        config = NotificationConfig(
            tenant_id=tenant_id,
            channel=channel,
            **data.model_dump(exclude_unset=True),
        )
        db.add(config)

    await db.flush()
    return config


async def get_notification_config(
    session_factory,
    tenant_id: uuid.UUID,
    channel: str,
) -> NotificationConfig | None:
    """Return an enabled NotificationConfig for (tenant, channel), or None."""
    async with session_factory() as session:
        result = await session.execute(
            select(NotificationConfig).where(
                NotificationConfig.tenant_id == tenant_id,
                NotificationConfig.channel == channel,
                NotificationConfig.is_enabled == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()


async def test_notification(tenant_id: uuid.UUID, channel: str, message: str) -> dict:
    """Placeholder — will send a test notification via the specified channel."""
    raise NotImplementedError(
        f"Test notification for channel '{channel}' not yet implemented. "
        "Will send via Slack webhook / SMTP / Twilio based on channel type."
    )
