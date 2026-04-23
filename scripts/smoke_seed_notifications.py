"""Seed NotificationConfig rows for the Phase 2 smoke test.

Reads the Slack webhook URL from SLACK_WEBHOOK_URL and the email recipient
from SMTP_FROM_EMAIL (both loaded from .env via pydantic-settings). Inserts
one NotificationConfig row per channel for the given tenant.

Usage:
    SMOKE_TENANT_ID=<uuid> PYTHONPATH=. py -3.12 scripts/smoke_seed_notifications.py
"""

import asyncio
import os
import sys
import uuid

from config.settings import settings
from src.models.notification_config import NotificationConfig
from src.services.database import async_session_factory


async def seed() -> None:
    tenant_id_str = os.environ.get("SMOKE_TENANT_ID")
    if not tenant_id_str:
        sys.exit("SMOKE_TENANT_ID env var required")

    tenant_id = uuid.UUID(tenant_id_str)
    webhook = settings.slack_webhook_url
    recipient = settings.smtp_from_email

    if not webhook:
        sys.exit("SLACK_WEBHOOK_URL not set in .env")
    if not recipient:
        sys.exit("SMTP_FROM_EMAIL not set in .env")

    async with async_session_factory() as s:
        s.add(
            NotificationConfig(
                tenant_id=tenant_id,
                channel="slack",
                is_enabled=True,
                use_platform_default=False,
                config={"webhook_url": webhook},
            )
        )
        s.add(
            NotificationConfig(
                tenant_id=tenant_id,
                channel="email",
                is_enabled=True,
                use_platform_default=False,
                config={"to": recipient},
            )
        )
        await s.commit()
        print(f"Seeded slack + email NotificationConfigs for tenant {tenant_id}")
        print(f"  slack webhook: {webhook[:40]}...")
        print(f"  email to:      {recipient}")


if __name__ == "__main__":
    asyncio.run(seed())
