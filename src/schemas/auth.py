import uuid
from datetime import datetime

from pydantic import BaseModel


class WsTokenResponse(BaseModel):
    token: str
    expires_in: int


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
    oauth_provider: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: UserResponse
    tenant_name: str
    tenant_slug: str
