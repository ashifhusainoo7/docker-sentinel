import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    use_platform_default: bool | None = None
    config: dict | None = None


class NotificationConfigResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    channel: str
    is_enabled: bool
    use_platform_default: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestNotificationRequest(BaseModel):
    message: str = "Test notification from DockerSentinel"
