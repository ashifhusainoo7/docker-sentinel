from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.tenant import Tenant
from src.schemas.notification import (
    NotificationConfigResponse,
    NotificationConfigUpdate,
    TestNotificationRequest,
)
from src.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/config", response_model=list[NotificationConfigResponse])
async def get_notification_configs(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_notification_configs(db, tenant.id)


@router.put("/config/{channel}", response_model=NotificationConfigResponse)
async def update_notification_config(
    channel: str,
    data: NotificationConfigUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.upsert_notification_config(
        db, tenant.id, channel, data
    )


@router.post("/test/{channel}")
async def test_notification(
    channel: str,
    body: TestNotificationRequest,
    tenant: Tenant = Depends(get_tenant),
):
    return await notification_service.test_notification(tenant.id, channel, body.message)
