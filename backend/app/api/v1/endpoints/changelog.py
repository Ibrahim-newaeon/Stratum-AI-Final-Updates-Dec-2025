# =============================================================================
# Stratum AI - Changelog / What's New Endpoints
# =============================================================================
"""
Product changelog and release notes:
- List changelog entries
- Get single entry
- Mark entries as read
- Admin: Create/update entries
"""

import contextlib
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import UserRole
from app.models.settings import (
    ChangelogEntry,
    ChangelogReadStatus,
    ChangelogType,
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/changelog", tags=["Changelog"])
logger = get_logger(__name__)


def _require_admin(request: Request) -> int:
    """Verify user has admin or superadmin role. Returns user_id."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_role = getattr(request.state, "role", None)
    if user_role not in (UserRole.ADMIN.value, UserRole.SUPERADMIN.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user_id


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ChangelogEntryResponse(BaseModel):
    """Changelog entry response."""

    id: int
    version: str
    title: str
    description: str
    type: str
    is_published: bool
    published_at: Optional[datetime]
    image_url: Optional[str]
    video_url: Optional[str]
    docs_url: Optional[str]
    tags: list[str]
    is_read: bool = False  # User-specific
    created_at: datetime


class ChangelogCreateRequest(BaseModel):
    """Request to create a changelog entry (admin only)."""

    version: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    type: str = Field(default="feature")
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    docs_url: Optional[str] = None
    tags: list[str] = Field(default=[])
    is_published: bool = Field(default=False)


class ChangelogUpdateRequest(BaseModel):
    """Request to update a changelog entry."""

    version: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    docs_url: Optional[str] = None
    tags: Optional[list[str]] = None
    is_published: Optional[bool] = None


class ChangelogSummaryResponse(BaseModel):
    """Summary of unread changelog entries."""

    unread_count: int
    latest_version: Optional[str]
    has_new_features: bool


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=APIResponse[list[ChangelogEntryResponse]])
async def list_changelog_entries(
    request: Request,
    include_unpublished: bool = False,
    type_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[list[ChangelogEntryResponse]]:
    """
    List changelog entries (public entries only, unless admin).
    """
    user_id = getattr(request.state, "user_id", None)

    conditions = []

    # Only admins may view unpublished entries
    if include_unpublished:
        user_role = getattr(request.state, "role", None)
        if user_role not in (UserRole.ADMIN.value, UserRole.SUPERADMIN.value):
            include_unpublished = False

    if not include_unpublished:
        conditions.append(ChangelogEntry.is_published == True)

    if type_filter:
        try:
            entry_type = ChangelogType(type_filter)
            conditions.append(ChangelogEntry.type == entry_type)
        except ValueError:
            pass

    query = select(ChangelogEntry)
    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(desc(ChangelogEntry.published_at), desc(ChangelogEntry.created_at))
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    entries = result.scalars().all()

    # Get read status for user
    read_ids = set()
    if user_id:
        read_result = await db.execute(
            select(ChangelogReadStatus.changelog_id).where(ChangelogReadStatus.user_id == user_id)
        )
        read_ids = set(read_result.scalars().all())

    return APIResponse(
        success=True,
        data=[
            ChangelogEntryResponse(
                id=e.id,
                version=e.version,
                title=e.title,
                description=e.description,
                type=e.type.value,
                is_published=e.is_published,
                published_at=e.published_at,
                image_url=e.image_url,
                video_url=e.video_url,
                docs_url=e.docs_url,
                tags=e.tags or [],
                is_read=e.id in read_ids,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


@router.get("/summary", response_model=APIResponse[ChangelogSummaryResponse])
async def get_changelog_summary(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ChangelogSummaryResponse]:
    """
    Get summary of changelog for the current user.
    """
    user_id = getattr(request.state, "user_id", None)

    # Get all published entries
    result = await db.execute(
        select(ChangelogEntry)
        .where(ChangelogEntry.is_published == True)
        .order_by(desc(ChangelogEntry.published_at))
    )
    entries = result.scalars().all()

    if not entries:
        return APIResponse(
            success=True,
            data=ChangelogSummaryResponse(
                unread_count=0,
                latest_version=None,
                has_new_features=False,
            ),
        )

    # Get read status for user
    read_ids = set()
    if user_id:
        read_result = await db.execute(
            select(ChangelogReadStatus.changelog_id).where(ChangelogReadStatus.user_id == user_id)
        )
        read_ids = set(read_result.scalars().all())

    unread_entries = [e for e in entries if e.id not in read_ids]
    has_new_features = any(e.type == ChangelogType.FEATURE for e in unread_entries)

    return APIResponse(
        success=True,
        data=ChangelogSummaryResponse(
            unread_count=len(unread_entries),
            latest_version=entries[0].version if entries else None,
            has_new_features=has_new_features,
        ),
    )


@router.get("/{entry_id}", response_model=APIResponse[ChangelogEntryResponse])
async def get_changelog_entry(
    request: Request,
    entry_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ChangelogEntryResponse]:
    """
    Get a specific changelog entry.
    """
    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(select(ChangelogEntry).where(ChangelogEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog entry not found",
        )

    # Check if user has read this entry
    is_read = False
    if user_id:
        read_result = await db.execute(
            select(ChangelogReadStatus).where(
                and_(
                    ChangelogReadStatus.user_id == user_id,
                    ChangelogReadStatus.changelog_id == entry_id,
                )
            )
        )
        is_read = read_result.scalar_one_or_none() is not None

    return APIResponse(
        success=True,
        data=ChangelogEntryResponse(
            id=entry.id,
            version=entry.version,
            title=entry.title,
            description=entry.description,
            type=entry.type.value,
            is_published=entry.is_published,
            published_at=entry.published_at,
            image_url=entry.image_url,
            video_url=entry.video_url,
            docs_url=entry.docs_url,
            tags=entry.tags or [],
            is_read=is_read,
            created_at=entry.created_at,
        ),
    )


@router.post("/{entry_id}/mark-read", response_model=APIResponse[dict])
async def mark_changelog_read(
    request: Request,
    entry_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[dict]:
    """
    Mark a changelog entry as read for the current user.
    """
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Verify entry exists
    result = await db.execute(select(ChangelogEntry).where(ChangelogEntry.id == entry_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog entry not found",
        )

    # Check if already read
    existing = await db.execute(
        select(ChangelogReadStatus).where(
            and_(
                ChangelogReadStatus.user_id == user_id,
                ChangelogReadStatus.changelog_id == entry_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        return APIResponse(success=True, data={"already_read": True})

    # Mark as read
    read_status = ChangelogReadStatus(
        user_id=user_id,
        changelog_id=entry_id,
        read_at=datetime.now(UTC),
    )
    db.add(read_status)
    await db.commit()

    return APIResponse(success=True, data={"marked_read": True})


@router.post("/mark-all-read", response_model=APIResponse[dict])
async def mark_all_changelog_read(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[dict]:
    """
    Mark all changelog entries as read for the current user.
    """
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Get all published entries
    result = await db.execute(select(ChangelogEntry.id).where(ChangelogEntry.is_published == True))
    all_entry_ids = set(result.scalars().all())

    # Get already read entries
    read_result = await db.execute(
        select(ChangelogReadStatus.changelog_id).where(ChangelogReadStatus.user_id == user_id)
    )
    already_read_ids = set(read_result.scalars().all())

    # Mark unread entries as read
    unread_ids = all_entry_ids - already_read_ids
    now = datetime.now(UTC)

    for entry_id in unread_ids:
        read_status = ChangelogReadStatus(
            user_id=user_id,
            changelog_id=entry_id,
            read_at=now,
        )
        db.add(read_status)

    await db.commit()

    return APIResponse(
        success=True,
        data={"marked_read": len(unread_ids)},
        message=f"{len(unread_ids)} entries marked as read",
    )


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.post(
    "", response_model=APIResponse[ChangelogEntryResponse], status_code=status.HTTP_201_CREATED
)
async def create_changelog_entry(
    request: Request,
    body: ChangelogCreateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ChangelogEntryResponse]:
    """
    Create a new changelog entry (admin only).
    """
    user_id = _require_admin(request)

    try:
        entry_type = ChangelogType(body.type)
    except ValueError:
        entry_type = ChangelogType.FEATURE

    entry = ChangelogEntry(
        version=body.version,
        title=body.title,
        description=body.description,
        type=entry_type,
        image_url=body.image_url,
        video_url=body.video_url,
        docs_url=body.docs_url,
        tags=body.tags,
        is_published=body.is_published,
        published_at=datetime.now(UTC) if body.is_published else None,
    )

    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    logger.info(f"Changelog entry created: {entry.id} - {entry.version}")

    return APIResponse(
        success=True,
        data=ChangelogEntryResponse(
            id=entry.id,
            version=entry.version,
            title=entry.title,
            description=entry.description,
            type=entry.type.value,
            is_published=entry.is_published,
            published_at=entry.published_at,
            image_url=entry.image_url,
            video_url=entry.video_url,
            docs_url=entry.docs_url,
            tags=entry.tags or [],
            is_read=False,
            created_at=entry.created_at,
        ),
    )


@router.patch("/{entry_id}", response_model=APIResponse[ChangelogEntryResponse])
async def update_changelog_entry(
    request: Request,
    entry_id: int,
    body: ChangelogUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ChangelogEntryResponse]:
    """
    Update a changelog entry (admin only).
    """
    user_id = _require_admin(request)

    result = await db.execute(select(ChangelogEntry).where(ChangelogEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog entry not found",
        )

    # Update fields
    if body.version is not None:
        entry.version = body.version
    if body.title is not None:
        entry.title = body.title
    if body.description is not None:
        entry.description = body.description
    if body.type is not None:
        with contextlib.suppress(ValueError):
            entry.type = ChangelogType(body.type)
    if body.image_url is not None:
        entry.image_url = body.image_url
    if body.video_url is not None:
        entry.video_url = body.video_url
    if body.docs_url is not None:
        entry.docs_url = body.docs_url
    if body.tags is not None:
        entry.tags = body.tags
    if body.is_published is not None:
        was_published = entry.is_published
        entry.is_published = body.is_published
        # Set published_at when first publishing
        if body.is_published and not was_published:
            entry.published_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(entry)

    return APIResponse(
        success=True,
        data=ChangelogEntryResponse(
            id=entry.id,
            version=entry.version,
            title=entry.title,
            description=entry.description,
            type=entry.type.value,
            is_published=entry.is_published,
            published_at=entry.published_at,
            image_url=entry.image_url,
            video_url=entry.video_url,
            docs_url=entry.docs_url,
            tags=entry.tags or [],
            is_read=False,
            created_at=entry.created_at,
        ),
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_changelog_entry(
    request: Request,
    entry_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete a changelog entry (admin only).
    """
    user_id = _require_admin(request)

    result = await db.execute(select(ChangelogEntry).where(ChangelogEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changelog entry not found",
        )

    await db.delete(entry)
    await db.commit()

    logger.info(f"Changelog entry deleted: {entry_id}")
