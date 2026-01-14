# =============================================================================
# Stratum AI - Automation Rules Engine Endpoints
# =============================================================================
"""
IFTTT-style automation rules management.
Implements Module C: Stratum Automation.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Rule, RuleExecution, RuleStatus
from app.schemas import (
    APIResponse,
    PaginatedResponse,
    RuleCreate,
    RuleExecutionResponse,
    RuleResponse,
    RuleUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=APIResponse[PaginatedResponse[RuleResponse]])
async def list_rules(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[RuleStatus] = None,
):
    """List automation rules."""
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(Rule).where(
        Rule.tenant_id == tenant_id,
        Rule.is_deleted == False,
    )

    if status:
        query = query.where(Rule.status == status)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Rule.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rules = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[RuleResponse.model_validate(r) for r in rules],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/{rule_id}", response_model=APIResponse[RuleResponse])
async def get_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Get rule details."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.tenant_id == tenant_id,
            Rule.is_deleted == False,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    return APIResponse(success=True, data=RuleResponse.model_validate(rule))


@router.post("", response_model=APIResponse[RuleResponse], status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: Request,
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new automation rule."""
    tenant_id = getattr(request.state, "tenant_id", None)

    rule = Rule(
        tenant_id=tenant_id,
        **rule_data.model_dump(),
    )

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    logger.info("rule_created", rule_id=rule.id, name=rule.name)

    return APIResponse(
        success=True,
        data=RuleResponse.model_validate(rule),
        message="Rule created successfully",
    )


@router.patch("/{rule_id}", response_model=APIResponse[RuleResponse])
async def update_rule(
    request: Request,
    rule_id: int,
    update_data: RuleUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a rule."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.tenant_id == tenant_id,
            Rule.is_deleted == False,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)

    logger.info("rule_updated", rule_id=rule_id)

    return APIResponse(
        success=True,
        data=RuleResponse.model_validate(rule),
        message="Rule updated successfully",
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Soft delete a rule."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.tenant_id == tenant_id,
            Rule.is_deleted == False,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    rule.soft_delete()
    await db.commit()

    logger.info("rule_deleted", rule_id=rule_id)


@router.post("/{rule_id}/activate", response_model=APIResponse[RuleResponse])
async def activate_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Activate a rule."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.tenant_id == tenant_id,
            Rule.is_deleted == False,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    rule.status = RuleStatus.ACTIVE
    await db.commit()
    await db.refresh(rule)

    logger.info("rule_activated", rule_id=rule_id)

    return APIResponse(
        success=True,
        data=RuleResponse.model_validate(rule),
        message="Rule activated",
    )


@router.post("/{rule_id}/pause", response_model=APIResponse[RuleResponse])
async def pause_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """Pause a rule."""
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.tenant_id == tenant_id,
            Rule.is_deleted == False,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    rule.status = RuleStatus.PAUSED
    await db.commit()
    await db.refresh(rule)

    logger.info("rule_paused", rule_id=rule_id)

    return APIResponse(
        success=True,
        data=RuleResponse.model_validate(rule),
        message="Rule paused",
    )


@router.post("/{rule_id}/test")
async def test_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Test a rule without executing actions.
    Returns what campaigns would be affected.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.tenant_id == tenant_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    # Evaluate rule in dry-run mode
    from app.services.rules_engine import RulesEngine

    engine = RulesEngine(db, tenant_id)
    test_results = await engine.evaluate_rule(rule, dry_run=True)

    return APIResponse(
        success=True,
        data=test_results,
        message="Rule test completed",
    )


@router.get("/{rule_id}/executions", response_model=APIResponse[List[RuleExecutionResponse]])
async def get_rule_executions(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_async_session),
    limit: int = Query(50, ge=1, le=200),
):
    """Get execution history for a rule."""
    tenant_id = getattr(request.state, "tenant_id", None)

    # Verify rule exists
    rule_result = await db.execute(
        select(Rule).where(Rule.id == rule_id, Rule.tenant_id == tenant_id)
    )
    if not rule_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    result = await db.execute(
        select(RuleExecution)
        .where(RuleExecution.rule_id == rule_id, RuleExecution.tenant_id == tenant_id)
        .order_by(RuleExecution.executed_at.desc())
        .limit(limit)
    )
    executions = result.scalars().all()

    return APIResponse(
        success=True,
        data=[RuleExecutionResponse.model_validate(e) for e in executions],
    )
