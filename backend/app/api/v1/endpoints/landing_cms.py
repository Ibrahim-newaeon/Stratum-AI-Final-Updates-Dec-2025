"""
Landing Page CMS API Endpoints
Manage landing page content with multi-language support
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import LandingContent, LandingContentHistory

router = APIRouter(prefix="/landing-cms", tags=["Landing CMS"])


# =============================================================================
# Pydantic Schemas
# =============================================================================
class ContentBase(BaseModel):
    section: str = Field(..., min_length=1, max_length=50)
    language: str = Field(default="en", min_length=2, max_length=10)
    content: dict = Field(default_factory=dict)


class ContentCreate(ContentBase):
    pass


class ContentUpdate(BaseModel):
    content: dict = Field(...)
    is_published: Optional[bool] = None


class ContentResponse(ContentBase):
    id: int
    is_published: bool
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    updated_by: Optional[int]

    class Config:
        from_attributes = True


class ContentHistoryResponse(BaseModel):
    id: int
    content_id: int
    section: str
    language: str
    content: dict
    version: int
    changed_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class BulkContentResponse(BaseModel):
    sections: dict[str, dict]  # section -> content


# =============================================================================
# Public Endpoints (for Landing Page)
# =============================================================================
@router.get("/public/all", response_model=BulkContentResponse)
async def get_all_published_content(
    language: str = Query(default="en", description="Language code (en, ar)"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get all published landing page content for a language.
    Used by the public landing page to fetch content.
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.language == language,
                LandingContent.is_published == True,
            )
        )
    )
    rows = result.scalars().all()

    sections = {}
    for row in rows:
        sections[row.section] = row.content

    return {"sections": sections}


@router.get("/public/{section}", response_model=dict)
async def get_published_section(
    section: str,
    language: str = Query(default="en", description="Language code"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get a specific published section content.
    Returns empty dict if section not found.
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
                LandingContent.is_published == True,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        return {}

    return row.content


# =============================================================================
# Admin Endpoints (require authentication)
# =============================================================================
@router.get("/admin/sections", response_model=List[ContentResponse])
async def list_all_sections(
    language: Optional[str] = Query(default=None, description="Filter by language"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    List all content sections (for admin panel).
    """
    query = select(LandingContent)
    if language:
        query = query.where(LandingContent.language == language)
    query = query.order_by(LandingContent.section, LandingContent.language)

    result = await session.execute(query)
    rows = result.scalars().all()

    return rows


@router.get("/admin/section/{section}", response_model=List[ContentResponse])
async def get_section_all_languages(
    section: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get a section in all available languages.
    """
    result = await session.execute(
        select(LandingContent)
        .where(LandingContent.section == section)
        .order_by(LandingContent.language)
    )
    rows = result.scalars().all()

    return rows


@router.get("/admin/section/{section}/{language}", response_model=ContentResponse)
async def get_section_by_language(
    section: str,
    language: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get a specific section in a specific language.
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    return row


@router.post("/admin/section", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    data: ContentCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Create a new section (for a new language variant).
    """
    # Check if section+language already exists
    existing = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == data.section,
                LandingContent.language == data.language,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Section '{data.section}' already exists for language '{data.language}'",
        )

    new_content = LandingContent(
        section=data.section,
        language=data.language,
        content=data.content,
        is_published=False,
        version=1,
    )

    session.add(new_content)
    await session.flush()
    await session.refresh(new_content)

    return new_content


@router.put("/admin/section/{section}/{language}", response_model=ContentResponse)
async def update_section(
    section: str,
    language: str,
    data: ContentUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Update a section's content.
    Creates a history record before updating.
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    # Save history before updating
    history = LandingContentHistory(
        content_id=row.id,
        section=row.section,
        language=row.language,
        content=row.content,
        version=row.version,
        changed_by=row.updated_by,
    )
    session.add(history)

    # Update the content
    row.content = data.content
    row.version += 1
    row.updated_at = datetime.now(timezone.utc)

    if data.is_published is not None:
        row.is_published = data.is_published
        if data.is_published:
            row.published_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(row)

    return row


@router.post("/admin/section/{section}/{language}/publish", response_model=ContentResponse)
async def publish_section(
    section: str,
    language: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Publish a section (make it live).
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    row.is_published = True
    row.published_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(row)

    return row


@router.post("/admin/section/{section}/{language}/unpublish", response_model=ContentResponse)
async def unpublish_section(
    section: str,
    language: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Unpublish a section (hide from public).
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    row.is_published = False

    await session.flush()
    await session.refresh(row)

    return row


@router.get("/admin/section/{section}/{language}/history", response_model=List[ContentHistoryResponse])
async def get_section_history(
    section: str,
    language: str,
    limit: int = Query(default=10, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get version history for a section.
    """
    # First get the content ID
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    # Get history
    history_result = await session.execute(
        select(LandingContentHistory)
        .where(LandingContentHistory.content_id == row.id)
        .order_by(LandingContentHistory.version.desc())
        .limit(limit)
    )
    history = history_result.scalars().all()

    return history


@router.post("/admin/section/{section}/{language}/rollback/{version}", response_model=ContentResponse)
async def rollback_section(
    section: str,
    language: str,
    version: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Rollback a section to a previous version.
    """
    # Get current content
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    # Get the history version to rollback to
    history_result = await session.execute(
        select(LandingContentHistory).where(
            and_(
                LandingContentHistory.content_id == row.id,
                LandingContentHistory.version == version,
            )
        )
    )
    history = history_result.scalar_one_or_none()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found in history",
        )

    # Save current state to history
    current_history = LandingContentHistory(
        content_id=row.id,
        section=row.section,
        language=row.language,
        content=row.content,
        version=row.version,
        changed_by=row.updated_by,
    )
    session.add(current_history)

    # Rollback to the old version
    row.content = history.content
    row.version += 1
    row.updated_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(row)

    return row


@router.delete("/admin/section/{section}/{language}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section: str,
    language: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Delete a section (and its history).
    Use with caution!
    """
    result = await session.execute(
        select(LandingContent).where(
            and_(
                LandingContent.section == section,
                LandingContent.language == language,
            )
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section}' not found for language '{language}'",
        )

    # Delete history first
    await session.execute(
        LandingContentHistory.__table__.delete().where(
            LandingContentHistory.content_id == row.id
        )
    )

    # Delete the content
    await session.delete(row)
    await session.flush()

    return None


# =============================================================================
# Utility Endpoints
# =============================================================================
@router.get("/languages", response_model=List[str])
async def get_available_languages(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get list of languages that have content.
    """
    result = await session.execute(
        select(LandingContent.language).distinct()
    )
    languages = [row[0] for row in result.all()]

    return sorted(languages)


@router.get("/sections", response_model=List[str])
async def get_available_sections(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get list of available section types.
    """
    result = await session.execute(
        select(LandingContent.section).distinct()
    )
    sections = [row[0] for row in result.all()]

    return sorted(sections)
