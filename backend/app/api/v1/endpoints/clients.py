# =============================================================================
# Stratum AI - Client Management Endpoints
# =============================================================================
"""
Client CRUD, user assignments, portal invitations, and KPI summaries.
All endpoints enforce tenant isolation and client-scope RBAC.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import (
    VerifiedUserDep,
    get_accessible_client_ids,
)
from app.auth.permissions import (
    PermLevel,
    can_manage_role,
    enforce_client_access,
    get_accessible_client_ids as perm_get_accessible,
    require_permission,
)
from app.base_schemas import APIResponse, PaginatedResponse
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign, CampaignStatus, User, UserRole
from app.models.client import Client, ClientAssignment
from app.schemas.client import (
    ClientAssignmentCreate,
    ClientAssignmentResponse,
    ClientCreate,
    ClientListResponse,
    ClientPortalInvite,
    ClientResponse,
    ClientSummaryResponse,
    ClientUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Client CRUD
# =============================================================================


@router.get("", response_model=APIResponse[PaginatedResponse[ClientListResponse]])
async def list_clients(
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    industry: Optional[str] = None,
):
    """List clients scoped by user role and assignments."""
    try:
        tenant_id = current_user.tenant_id
        user = current_user.user

        # Get accessible client IDs based on role
        accessible_ids = await perm_get_accessible(
            user_id=user.id,
            user_role=user.role,
            tenant_id=tenant_id,
            db=db,
            client_id=getattr(user, "client_id", None),
        )

        query = select(Client).where(
            Client.tenant_id == tenant_id,
            Client.is_deleted == False,
        )

        if accessible_ids is not None:
            query = query.where(Client.id.in_(accessible_ids))

        if search:
            query = query.where(Client.name.ilike(f"%{search}%"))
        if is_active is not None:
            query = query.where(Client.is_active == is_active)
        if industry:
            query = query.where(Client.industry == industry)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(Client.name).offset(offset).limit(page_size)
        result = await db.execute(query)
        clients = result.scalars().all()

        # Enrich with campaign counts
        items = []
        for c in clients:
            camp_count = await db.execute(
                select(func.count()).select_from(
                    select(Campaign.id).where(
                        Campaign.client_id == c.id,
                        Campaign.is_deleted == False,
                    ).subquery()
                )
            )
            spend_result = await db.execute(
                select(func.coalesce(func.sum(Campaign.total_spend_cents), 0)).where(
                    Campaign.client_id == c.id,
                    Campaign.is_deleted == False,
                )
            )
            item = ClientListResponse.model_validate(c)
            item.total_campaigns = camp_count.scalar() or 0
            item.total_spend_cents = spend_result.scalar() or 0
            items.append(item)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return APIResponse(
            data=PaginatedResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing clients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list clients",
        )


@router.post(
    "",
    response_model=APIResponse[ClientResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("clients", PermLevel.FULL))],
)
async def create_client(
    payload: ClientCreate,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new client. Requires ADMIN+ role."""
    try:
        tenant_id = current_user.tenant_id

        # Check tier limit
        from app.auth.deps import check_tier_limit

        await check_tier_limit("clients", tenant_id, db)

        # Check slug uniqueness within tenant
        existing = await db.execute(
            select(Client.id).where(
                Client.tenant_id == tenant_id,
                Client.slug == payload.slug,
                Client.is_deleted == False,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Client with slug '{payload.slug}' already exists",
            )

        client = Client(
            tenant_id=tenant_id,
            **payload.model_dump(exclude_unset=False),
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)

        logger.info(f"Client created: {client.id} by user {current_user.id}")
        return APIResponse(
            data=ClientResponse.model_validate(client),
            message="Client created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client",
        )


@router.get("/{client_id}", response_model=APIResponse[ClientResponse])
async def get_client(
    client_id: int,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Get client detail (scoped by role)."""
    try:
        tenant_id = current_user.tenant_id
        user = current_user.user

        # Enforce client access
        await enforce_client_access(
            user_id=user.id,
            user_role=user.role,
            client_id=client_id,
            tenant_id=tenant_id,
            db=db,
            user_client_id=getattr(user, "client_id", None),
        )

        result = await db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
                Client.is_deleted == False,
            )
        )
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Enrich
        response = ClientResponse.model_validate(client)

        camp_count = await db.execute(
            select(func.count()).select_from(
                select(Campaign.id).where(
                    Campaign.client_id == client_id,
                    Campaign.is_deleted == False,
                ).subquery()
            )
        )
        response.total_campaigns = camp_count.scalar() or 0

        spend_result = await db.execute(
            select(func.coalesce(func.sum(Campaign.total_spend_cents), 0)).where(
                Campaign.client_id == client_id,
                Campaign.is_deleted == False,
            )
        )
        response.total_spend_cents = spend_result.scalar() or 0

        # Assigned user IDs
        assign_result = await db.execute(
            select(ClientAssignment.user_id).where(
                ClientAssignment.client_id == client_id,
            )
        )
        response.assigned_users = list(assign_result.scalars().all())

        return APIResponse(data=response)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get client",
        )


@router.patch(
    "/{client_id}",
    response_model=APIResponse[ClientResponse],
    dependencies=[Depends(require_permission("clients", PermLevel.EDIT))],
)
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a client. Requires MANAGER+ role."""
    try:
        tenant_id = current_user.tenant_id
        user = current_user.user

        await enforce_client_access(
            user_id=user.id,
            user_role=user.role,
            client_id=client_id,
            tenant_id=tenant_id,
            db=db,
            user_client_id=getattr(user, "client_id", None),
        )

        result = await db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
                Client.is_deleted == False,
            )
        )
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        update_data = payload.model_dump(exclude_unset=True)

        # Check slug uniqueness if slug is being changed
        if "slug" in update_data and update_data["slug"] != client.slug:
            slug_check = await db.execute(
                select(Client.id).where(
                    Client.tenant_id == tenant_id,
                    Client.slug == update_data["slug"],
                    Client.is_deleted == False,
                    Client.id != client_id,
                )
            )
            if slug_check.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Client with slug '{update_data['slug']}' already exists",
                )

        for field, value in update_data.items():
            setattr(client, field, value)

        await db.commit()
        await db.refresh(client)

        logger.info(f"Client updated: {client_id} by user {current_user.id}")
        return APIResponse(
            data=ClientResponse.model_validate(client),
            message="Client updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client",
        )


@router.delete(
    "/{client_id}",
    response_model=APIResponse,
    dependencies=[Depends(require_permission("clients", PermLevel.FULL))],
)
async def delete_client(
    client_id: int,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Soft-delete a client. Requires ADMIN+ role."""
    try:
        tenant_id = current_user.tenant_id

        result = await db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
                Client.is_deleted == False,
            )
        )
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        client.soft_delete()
        await db.commit()

        logger.info(f"Client soft-deleted: {client_id} by user {current_user.id}")
        return APIResponse(message="Client deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client",
        )


@router.get("/{client_id}/summary", response_model=APIResponse[ClientSummaryResponse])
async def get_client_summary(
    client_id: int,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Aggregated KPI summary across all campaigns for a client."""
    try:
        tenant_id = current_user.tenant_id
        user = current_user.user

        await enforce_client_access(
            user_id=user.id,
            user_role=user.role,
            client_id=client_id,
            tenant_id=tenant_id,
            db=db,
            user_client_id=getattr(user, "client_id", None),
        )

        # Fetch client
        client_result = await db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
                Client.is_deleted == False,
            )
        )
        client = client_result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Aggregate campaign metrics
        base_filter = [
            Campaign.client_id == client_id,
            Campaign.is_deleted == False,
        ]

        total_count = await db.execute(
            select(func.count()).select_from(
                select(Campaign.id).where(*base_filter).subquery()
            )
        )
        active_count = await db.execute(
            select(func.count()).select_from(
                select(Campaign.id).where(
                    *base_filter, Campaign.status == CampaignStatus.ACTIVE
                ).subquery()
            )
        )

        agg_result = await db.execute(
            select(
                func.coalesce(func.sum(Campaign.total_spend_cents), 0),
                func.coalesce(func.sum(Campaign.revenue_cents), 0),
                func.coalesce(func.sum(Campaign.impressions), 0),
                func.coalesce(func.sum(Campaign.clicks), 0),
                func.coalesce(func.sum(Campaign.conversions), 0),
            ).where(*base_filter)
        )
        agg = agg_result.one()

        total_spend = agg[0]
        total_revenue = agg[1]
        total_impressions = agg[2]
        total_clicks = agg[3]
        total_conversions = agg[4]

        avg_roas = (total_revenue / total_spend) if total_spend > 0 else None
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else None
        avg_cpa = int(total_spend / total_conversions) if total_conversions > 0 else None

        budget_util = None
        if client.monthly_budget_cents and client.monthly_budget_cents > 0:
            budget_util = round(total_spend / client.monthly_budget_cents, 4)

        summary = ClientSummaryResponse(
            client_id=client_id,
            client_name=client.name,
            total_campaigns=total_count.scalar() or 0,
            active_campaigns=active_count.scalar() or 0,
            total_spend_cents=total_spend,
            total_revenue_cents=total_revenue,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            avg_roas=avg_roas,
            avg_ctr=avg_ctr,
            avg_cpa_cents=avg_cpa,
            monthly_budget_cents=client.monthly_budget_cents,
            budget_utilization=budget_util,
        )

        return APIResponse(data=summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client summary {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get client summary",
        )


# =============================================================================
# Client Assignments
# =============================================================================


@router.get(
    "/{client_id}/assignments",
    response_model=APIResponse[list[ClientAssignmentResponse]],
    dependencies=[Depends(require_permission("clients", PermLevel.VIEW))],
)
async def list_assignments(
    client_id: int,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """List users assigned to a client."""
    try:
        tenant_id = current_user.tenant_id
        user = current_user.user

        await enforce_client_access(
            user_id=user.id,
            user_role=user.role,
            client_id=client_id,
            tenant_id=tenant_id,
            db=db,
            user_client_id=getattr(user, "client_id", None),
        )

        result = await db.execute(
            select(ClientAssignment).where(
                ClientAssignment.client_id == client_id,
            )
        )
        assignments = result.scalars().all()

        items = []
        for a in assignments:
            item = ClientAssignmentResponse(
                id=a.id,
                user_id=a.user_id,
                client_id=a.client_id,
                assigned_by=a.assigned_by,
                is_primary=a.is_primary,
                created_at=a.created_at,
            )

            # Enrich with user info
            user_result = await db.execute(
                select(User).where(User.id == a.user_id)
            )
            assigned_user = user_result.scalar_one_or_none()
            if assigned_user:
                from app.core.security import decrypt_pii

                item.user_email = decrypt_pii(assigned_user.email)
                item.user_name = decrypt_pii(assigned_user.full_name) if assigned_user.full_name else None
                item.user_role = assigned_user.role.value
            items.append(item)

        return APIResponse(data=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing assignments for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list assignments",
        )


@router.post(
    "/{client_id}/assignments",
    response_model=APIResponse[ClientAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("clients", PermLevel.FULL))],
)
async def create_assignment(
    client_id: int,
    payload: ClientAssignmentCreate,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Assign a user to a client. Requires ADMIN+ role."""
    try:
        tenant_id = current_user.tenant_id

        # Verify client exists in tenant
        client_check = await db.execute(
            select(Client.id).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
                Client.is_deleted == False,
            )
        )
        if client_check.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Verify target user exists in same tenant
        user_check = await db.execute(
            select(User).where(
                User.id == payload.user_id,
                User.tenant_id == tenant_id,
                User.is_deleted == False,
            )
        )
        target_user = user_check.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant",
            )

        # Only MANAGER and ANALYST should be assigned via this route
        if target_user.role not in (UserRole.MANAGER, UserRole.ANALYST):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only MANAGER and ANALYST users can be assigned to clients via assignments",
            )

        # Check duplicate
        dup_check = await db.execute(
            select(ClientAssignment.id).where(
                ClientAssignment.user_id == payload.user_id,
                ClientAssignment.client_id == client_id,
            )
        )
        if dup_check.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already assigned to this client",
            )

        assignment = ClientAssignment(
            user_id=payload.user_id,
            client_id=client_id,
            assigned_by=current_user.id,
            is_primary=payload.is_primary,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        logger.info(
            f"User {payload.user_id} assigned to client {client_id} by {current_user.id}"
        )
        return APIResponse(
            data=ClientAssignmentResponse(
                id=assignment.id,
                user_id=assignment.user_id,
                client_id=assignment.client_id,
                assigned_by=assignment.assigned_by,
                is_primary=assignment.is_primary,
                created_at=assignment.created_at,
            ),
            message="User assigned to client successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating assignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create assignment",
        )


@router.delete(
    "/{client_id}/assignments/{user_id}",
    response_model=APIResponse,
    dependencies=[Depends(require_permission("clients", PermLevel.FULL))],
)
async def delete_assignment(
    client_id: int,
    user_id: int,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Unassign a user from a client. Requires ADMIN+ role."""
    try:
        result = await db.execute(
            select(ClientAssignment).where(
                ClientAssignment.user_id == user_id,
                ClientAssignment.client_id == client_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found",
            )

        await db.delete(assignment)
        await db.commit()

        logger.info(
            f"User {user_id} unassigned from client {client_id} by {current_user.id}"
        )
        return APIResponse(message="User unassigned from client successfully")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting assignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete assignment",
        )


# =============================================================================
# Portal Invitations
# =============================================================================


@router.post(
    "/{client_id}/invite-portal",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("clients.portal_users", PermLevel.EDIT))],
)
async def invite_portal_user(
    client_id: int,
    payload: ClientPortalInvite,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """Invite a client portal user (VIEWER role with client scope). Requires ADMIN+."""
    try:
        tenant_id = current_user.tenant_id

        # Check tier limit for users
        from app.auth.deps import check_tier_limit

        await check_tier_limit("users", tenant_id, db)

        # Verify client exists
        client_check = await db.execute(
            select(Client.id).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
                Client.is_deleted == False,
            )
        )
        if client_check.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Check if email already exists in tenant
        from app.core.security import encrypt_pii, hash_email

        email_h = hash_email(payload.email)
        existing = await db.execute(
            select(User.id).where(
                User.tenant_id == tenant_id,
                User.email_hash == email_h,
                User.is_deleted == False,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists in the tenant",
            )

        # Create portal user
        from app.core.security import get_password_hash

        import secrets

        temp_password = secrets.token_urlsafe(16)

        portal_user = User(
            tenant_id=tenant_id,
            email=encrypt_pii(payload.email),
            email_hash=email_h,
            password_hash=get_password_hash(temp_password),
            full_name=encrypt_pii(payload.full_name),
            role=UserRole.VIEWER,
            client_id=client_id,
            user_type="portal",
            is_active=True,
            is_verified=False,
        )
        db.add(portal_user)
        await db.commit()
        await db.refresh(portal_user)

        logger.info(
            f"Portal user created: {portal_user.id} for client {client_id} by {current_user.id}"
        )
        return APIResponse(
            message="Portal user invited successfully. They will receive an email to set their password.",
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inviting portal user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invite portal user",
        )
