import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["agent"]
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(BaseModel):
    """Returned only on creation — includes the full key (shown once)."""

    id: uuid.UUID
    name: str
    key: str  # Full API key — only shown once
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None
