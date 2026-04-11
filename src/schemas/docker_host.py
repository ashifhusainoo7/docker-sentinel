import uuid
from datetime import datetime

from pydantic import BaseModel


class DockerHostCreate(BaseModel):
    name: str
    connection_mode: str  # 'tcp' | 'agent'
    tcp_url: str | None = None
    tls_enabled: bool = False
    monitor_all_containers: bool = True
    container_filter: list[dict] = []


class DockerHostUpdate(BaseModel):
    name: str | None = None
    tcp_url: str | None = None
    tls_enabled: bool | None = None
    is_active: bool | None = None
    monitor_all_containers: bool | None = None
    container_filter: list[dict] | None = None


class DockerHostResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    connection_mode: str
    tcp_url: str | None
    tls_enabled: bool
    agent_id: str | None
    agent_last_seen: datetime | None
    is_active: bool
    monitor_all_containers: bool
    container_filter: list[dict]
    status: str
    status_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContainerInfo(BaseModel):
    container_id: str
    name: str
    image: str
    status: str
    created: datetime
