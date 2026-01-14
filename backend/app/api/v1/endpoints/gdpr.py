# =============================================================================
# Stratum AI - GDPR Compliance Endpoints
# =============================================================================
"""
GDPR compliance endpoints including data export and right to be forgotten.
Implements Module F: Security & Governance.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import anonymize_pii, decrypt_pii
from app.db.session import get_async_session
from app.models import (
    AuditAction,
    AuditLog,
    User,
    NotificationPreference,
    APIKey,
)
from app.schemas import (
    APIResponse,
    AuditLogResponse,
    GDPRAnonymizeRequest,
    GDPRAnonymizeResponse,
    GDPRExportRequest,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/export")
async def export_user_data(
    request: Request,
    export_request: GDPRExportRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Export all data associated with a user (GDPR Data Portability).

    Returns a JSON file containing all user data.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    requesting_user_id = getattr(request.state, "user_id", None)

    # Verify the user exists and belongs to the tenant
    result = await db.execute(
        select(User).where(
            User.id == export_request.user_id,
            User.tenant_id == tenant_id,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Only allow users to export their own data, or admins to export any data
    requesting_result = await db.execute(
        select(User).where(User.id == requesting_user_id)
    )
    requesting_user = requesting_result.scalar_one_or_none()

    if requesting_user_id != export_request.user_id:
        if not requesting_user or requesting_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to export this user's data",
            )

    # Collect user data
    export_data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "user_id": user.id,
        "profile": {
            "email": decrypt_pii(user.email),
            "full_name": decrypt_pii(user.full_name) if user.full_name else None,
            "phone": decrypt_pii(user.phone) if user.phone else None,
            "role": user.role.value,
            "locale": user.locale,
            "timezone": user.timezone,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "preferences": user.preferences,
            "consent_marketing": user.consent_marketing,
            "consent_analytics": user.consent_analytics,
        },
    }

    # Get notification preferences
    notif_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id
        )
    )
    notif_pref = notif_result.scalar_one_or_none()
    if notif_pref:
        export_data["notification_preferences"] = {
            "email_enabled": notif_pref.email_enabled,
            "slack_enabled": notif_pref.slack_enabled,
            "alert_rule_triggered": notif_pref.alert_rule_triggered,
            "alert_budget_threshold": notif_pref.alert_budget_threshold,
            "report_daily": notif_pref.report_daily,
            "report_weekly": notif_pref.report_weekly,
        }

    # Get API keys (without the actual key)
    api_keys_result = await db.execute(
        select(APIKey).where(APIKey.user_id == user.id)
    )
    api_keys = api_keys_result.scalars().all()
    export_data["api_keys"] = [
        {
            "name": key.name,
            "key_prefix": key.key_prefix,
            "created_at": key.created_at.isoformat(),
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "is_active": key.is_active,
        }
        for key in api_keys
    ]

    # Get audit logs if requested
    if export_request.include_audit_logs:
        audit_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(1000)
        )
        audit_logs = audit_result.scalars().all()
        export_data["audit_logs"] = [
            {
                "action": log.action.value,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "created_at": log.created_at.isoformat(),
                "ip_address": log.ip_address,
            }
            for log in audit_logs
        ]

    # Log the export action
    export_log = AuditLog(
        tenant_id=tenant_id,
        user_id=requesting_user_id,
        action=AuditAction.EXPORT,
        resource_type="user",
        resource_id=str(user.id),
        new_value={"export_type": "gdpr_data_export"},
    )
    db.add(export_log)
    await db.commit()

    logger.info(
        "gdpr_data_exported",
        user_id=user.id,
        requested_by=requesting_user_id,
    )

    # Return as downloadable JSON file
    def generate():
        yield json.dumps(export_data, indent=2, default=str)

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=user_data_export_{user.id}_{datetime.now().strftime('%Y%m%d')}.json"
        },
    )


@router.post("/anonymize", response_model=APIResponse[GDPRAnonymizeResponse])
async def anonymize_user_data(
    request: Request,
    anonymize_request: GDPRAnonymizeRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Anonymize all personal data for a user (GDPR Right to be Forgotten).

    This permanently removes all PII associated with the user while preserving
    non-personal data for analytics purposes.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    requesting_user_id = getattr(request.state, "user_id", None)

    # Verify confirmation
    if anonymize_request.confirmation != "CONFIRM_DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation. Must be 'CONFIRM_DELETE'",
        )

    # Get the user
    result = await db.execute(
        select(User).where(
            User.id == anonymize_request.user_id,
            User.tenant_id == tenant_id,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already anonymized
    if user.gdpr_anonymized_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User data has already been anonymized",
        )

    # Verify authorization (self or admin)
    requesting_result = await db.execute(
        select(User).where(User.id == requesting_user_id)
    )
    requesting_user = requesting_result.scalar_one_or_none()

    if requesting_user_id != anonymize_request.user_id:
        if not requesting_user or requesting_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to anonymize this user's data",
            )

    tables_affected = []
    records_modified = 0

    # Anonymize user record
    anon_email = anonymize_pii("email")
    anon_name = anonymize_pii("name")

    user.email = anon_email
    user.email_hash = f"ANON_{user.id}"
    user.full_name = anon_name
    user.phone = None
    user.avatar_url = None
    user.is_active = False
    user.gdpr_anonymized_at = datetime.now(timezone.utc)
    user.preferences = {}

    tables_affected.append("users")
    records_modified += 1

    # Delete notification preferences
    await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id
        )
    )
    # Actually delete
    from sqlalchemy import delete
    result = await db.execute(
        delete(NotificationPreference).where(
            NotificationPreference.user_id == user.id
        )
    )
    if result.rowcount > 0:
        tables_affected.append("notification_preferences")
        records_modified += result.rowcount

    # Delete API keys
    result = await db.execute(
        delete(APIKey).where(APIKey.user_id == user.id)
    )
    if result.rowcount > 0:
        tables_affected.append("api_keys")
        records_modified += result.rowcount

    # Anonymize audit logs (keep structure, remove PII)
    result = await db.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user.id)
        .values(
            ip_address=None,
            user_agent=None,
        )
    )
    if result.rowcount > 0:
        tables_affected.append("audit_logs")
        records_modified += result.rowcount

    # Create audit log for the anonymization
    anonymization_log = AuditLog(
        tenant_id=tenant_id,
        user_id=requesting_user_id,
        action=AuditAction.ANONYMIZE,
        resource_type="user",
        resource_id=str(user.id),
        new_value={
            "tables_affected": tables_affected,
            "records_modified": records_modified,
        },
    )
    db.add(anonymization_log)

    await db.commit()

    logger.info(
        "gdpr_user_anonymized",
        user_id=user.id,
        requested_by=requesting_user_id,
        tables_affected=tables_affected,
        records_modified=records_modified,
    )

    return APIResponse(
        success=True,
        data=GDPRAnonymizeResponse(
            user_id=user.id,
            anonymized_at=user.gdpr_anonymized_at,
            tables_affected=tables_affected,
            records_modified=records_modified,
        ),
        message="User data has been anonymized",
    )


@router.get("/audit-logs", response_model=APIResponse[PaginatedResponse[AuditLogResponse]])
async def get_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = 1,
    page_size: int = 50,
    user_id: int = None,
    action: AuditAction = None,
    resource_type: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """
    Get audit logs for compliance reporting.

    Filterable by user, action type, resource, and date range.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    # Count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.post("/consent")
async def update_consent(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    consent_marketing: bool = None,
    consent_analytics: bool = None,
):
    """
    Update user consent preferences.
    """
    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if consent_marketing is not None:
        user.consent_marketing = consent_marketing
    if consent_analytics is not None:
        user.consent_analytics = consent_analytics

    await db.commit()

    logger.info(
        "consent_updated",
        user_id=user_id,
        consent_marketing=consent_marketing,
        consent_analytics=consent_analytics,
    )

    return APIResponse(
        success=True,
        data={
            "consent_marketing": user.consent_marketing,
            "consent_analytics": user.consent_analytics,
        },
        message="Consent preferences updated",
    )
