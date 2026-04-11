import uuid
from datetime import datetime

from pydantic import BaseModel


class EscalationRuleCreate(BaseModel):
    name: str
    condition: dict  # e.g. {"type": "multi_crash", "threshold": 2, "window_minutes": 5}
    action: str  # 'slack' | 'email' | 'call'


class EscalationRuleUpdate(BaseModel):
    name: str | None = None
    condition: dict | None = None
    action: str | None = None
    is_active: bool | None = None


class EscalationRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    condition: dict
    action: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
