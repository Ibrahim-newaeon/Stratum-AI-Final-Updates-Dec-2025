# =============================================================================
# Stratum AI - Landing Page CMS Endpoints
# =============================================================================
"""
Landing Page CMS endpoints for multi-language content management.

Routes:
- GET /landing-cms/health - Health check
- GET /landing-cms/pages - List published pages
- GET /landing-cms/pages/{slug} - Get page by slug
- GET /landing-cms/posts - List published posts
- GET /landing-cms/posts/{slug} - Get post by slug
- GET /landing-cms/categories - List categories
- GET /landing-cms/tags - List tags
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_async_session
from app.models.cms import (
    CMSPost,
    CMSPage,
    CMSCategory,
    CMSTag,
    CMSPostStatus,
    CMSPageStatus,
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/landing-cms")


@router.get("/health")
async def landing_cms_health():
    """Health check for Landing CMS module."""
    return {"status": "healthy", "module": "landing_cms"}


# =============================================================================
# Public Pages
# =============================================================================


@router.get("/pages", response_model=APIResponse[Dict[str, Any]])
async def list_published_pages(
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    navigation_only: bool = Query(False, description="Only return pages in navigation"),
):
    """List all published landing pages."""
    query = select(CMSPage).where(CMSPage.status == CMSPageStatus.published)

    if navigation_only:
        query = query.where(CMSPage.show_in_navigation == True)

    # Get total count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get pages with ordering
    query = query.order_by(CMSPage.navigation_order.asc(), CMSPage.title.asc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    pages = result.scalars().all()

    page_list = []
    for page in pages:
        page_list.append({
            "id": str(page.id),
            "title": page.title,
            "slug": page.slug,
            "meta_title": getattr(page, "meta_title", None),
            "meta_description": getattr(page, "meta_description", None),
            "show_in_navigation": page.show_in_navigation,
            "navigation_label": getattr(page, "navigation_label", None),
            "navigation_order": page.navigation_order,
            "published_at": page.published_at.isoformat() if page.published_at else None,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        })

    return APIResponse(
        success=True,
        data={
            "pages": page_list,
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get("/pages/{slug}", response_model=APIResponse[Dict[str, Any]])
async def get_page_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single published page by slug."""
    result = await db.execute(
        select(CMSPage).where(
            and_(
                CMSPage.slug == slug,
                CMSPage.status == CMSPageStatus.published,
            )
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with slug '{slug}' not found",
        )

    return APIResponse(
        success=True,
        data={
            "id": str(page.id),
            "title": page.title,
            "slug": page.slug,
            "content": page.content,
            "content_json": page.content_json,
            "meta_title": getattr(page, "meta_title", None),
            "meta_description": getattr(page, "meta_description", None),
            "published_at": page.published_at.isoformat() if page.published_at else None,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        },
    )


# =============================================================================
# Public Posts (Blog / Resources)
# =============================================================================


@router.get("/posts", response_model=APIResponse[Dict[str, Any]])
async def list_published_posts(
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category slug"),
    tag: Optional[str] = Query(None, description="Filter by tag slug"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    featured: Optional[bool] = Query(None, description="Filter featured posts only"),
):
    """List published blog posts and resources."""
    query = select(CMSPost).where(CMSPost.status == CMSPostStatus.published)

    if category:
        query = query.join(CMSPost.category).where(CMSCategory.slug == category)

    if tag:
        query = query.join(CMSPost.tags).where(CMSTag.slug == tag)

    if content_type:
        query = query.where(CMSPost.content_type == content_type)

    if featured is not None:
        query = query.where(CMSPost.is_featured == featured)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch with relationships
    query = query.options(
        selectinload(CMSPost.author),
        selectinload(CMSPost.category),
        selectinload(CMSPost.tags),
    )
    query = query.order_by(CMSPost.published_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().unique().all()

    post_list = []
    for post in posts:
        post_list.append({
            "id": str(post.id),
            "title": post.title,
            "slug": post.slug,
            "excerpt": post.excerpt,
            "content_type": post.content_type.value if post.content_type else None,
            "featured_image_url": getattr(post, "featured_image_url", None),
            "is_featured": post.is_featured,
            "author": {
                "name": post.author.name,
                "avatar_url": getattr(post.author, "avatar_url", None),
            } if post.author else None,
            "category": {
                "name": post.category.name,
                "slug": post.category.slug,
            } if post.category else None,
            "tags": [{"name": t.name, "slug": t.slug} for t in post.tags] if post.tags else [],
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "reading_time_minutes": getattr(post, "reading_time_minutes", None),
        })

    return APIResponse(
        success=True,
        data={
            "posts": post_list,
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get("/posts/{slug}", response_model=APIResponse[Dict[str, Any]])
async def get_post_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single published post by slug."""
    result = await db.execute(
        select(CMSPost)
        .where(
            and_(
                CMSPost.slug == slug,
                CMSPost.status == CMSPostStatus.published,
            )
        )
        .options(
            selectinload(CMSPost.author),
            selectinload(CMSPost.category),
            selectinload(CMSPost.tags),
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with slug '{slug}' not found",
        )

    return APIResponse(
        success=True,
        data={
            "id": str(post.id),
            "title": post.title,
            "slug": post.slug,
            "excerpt": post.excerpt,
            "content": post.content,
            "content_json": post.content_json,
            "content_type": post.content_type.value if post.content_type else None,
            "featured_image_url": getattr(post, "featured_image_url", None),
            "og_image_url": getattr(post, "og_image_url", None),
            "is_featured": post.is_featured,
            "meta_title": getattr(post, "meta_title", None),
            "meta_description": getattr(post, "meta_description", None),
            "author": {
                "name": post.author.name,
                "bio": getattr(post.author, "bio", None),
                "avatar_url": getattr(post.author, "avatar_url", None),
            } if post.author else None,
            "category": {
                "name": post.category.name,
                "slug": post.category.slug,
            } if post.category else None,
            "tags": [{"name": t.name, "slug": t.slug} for t in post.tags] if post.tags else [],
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None,
            "reading_time_minutes": getattr(post, "reading_time_minutes", None),
        },
    )


# =============================================================================
# Categories & Tags
# =============================================================================


@router.get("/categories", response_model=APIResponse[Dict[str, Any]])
async def list_categories(
    db: AsyncSession = Depends(get_async_session),
):
    """List all content categories."""
    result = await db.execute(
        select(CMSCategory).order_by(CMSCategory.display_order.asc(), CMSCategory.name.asc()).limit(1000)
    )
    categories = result.scalars().all()

    return APIResponse(
        success=True,
        data={
            "categories": [
                {
                    "id": str(cat.id),
                    "name": cat.name,
                    "slug": cat.slug,
                    "color": getattr(cat, "color", None),
                    "icon": getattr(cat, "icon", None),
                    "display_order": cat.display_order,
                }
                for cat in categories
            ],
        },
    )


@router.get("/tags", response_model=APIResponse[Dict[str, Any]])
async def list_tags(
    db: AsyncSession = Depends(get_async_session),
):
    """List all content tags."""
    result = await db.execute(
        select(CMSTag).order_by(CMSTag.usage_count.desc(), CMSTag.name.asc()).limit(1000)
    )
    tags = result.scalars().all()

    return APIResponse(
        success=True,
        data={
            "tags": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "slug": t.slug,
                    "usage_count": t.usage_count,
                }
                for t in tags
            ],
        },
    )
