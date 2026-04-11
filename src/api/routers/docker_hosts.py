import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.tenant import Tenant
from src.schemas.docker_host import (
    ContainerInfo,
    DockerHostCreate,
    DockerHostResponse,
    DockerHostUpdate,
)
from src.services import docker_host_service

router = APIRouter(prefix="/api/v1/hosts", tags=["docker-hosts"])


@router.get("", response_model=list[DockerHostResponse])
async def list_hosts(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await docker_host_service.list_hosts(db, tenant.id)


@router.post("", response_model=DockerHostResponse, status_code=201)
async def create_host(
    data: DockerHostCreate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await docker_host_service.create_host(db, tenant.id, data)


@router.get("/{host_id}", response_model=DockerHostResponse)
async def get_host(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    host = await docker_host_service.get_host(db, tenant.id, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.patch("/{host_id}", response_model=DockerHostResponse)
async def update_host(
    host_id: uuid.UUID,
    data: DockerHostUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    host = await docker_host_service.update_host(db, tenant.id, host_id, data)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.delete("/{host_id}", status_code=204)
async def delete_host(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    deleted = await docker_host_service.delete_host(db, tenant.id, host_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Host not found")


@router.post("/{host_id}/test")
async def test_connection(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await docker_host_service.test_host_connection(db, tenant.id, host_id)


@router.get("/{host_id}/containers", response_model=list[ContainerInfo])
async def list_containers(
    host_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
):
    raise NotImplementedError(
        "Container listing not yet implemented. "
        "Will connect to Docker host and list running containers."
    )
