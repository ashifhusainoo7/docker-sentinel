import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tenant
from src.models.escalation_rule import EscalationRule
from src.models.tenant import Tenant
from src.schemas.escalation import (
    EscalationRuleCreate,
    EscalationRuleResponse,
    EscalationRuleUpdate,
)

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])


@router.get("", response_model=list[EscalationRuleResponse])
async def list_rules(
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationRule).where(EscalationRule.tenant_id == tenant.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=EscalationRuleResponse, status_code=201)
async def create_rule(
    data: EscalationRuleCreate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    rule = EscalationRule(tenant_id=tenant.id, **data.model_dump())
    db.add(rule)
    await db.flush()
    return rule


@router.patch("/{rule_id}", response_model=EscalationRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: EscalationRuleUpdate,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationRule).where(
            EscalationRule.id == rule_id, EscalationRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    tenant: Tenant = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationRule).where(
            EscalationRule.id == rule_id, EscalationRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
