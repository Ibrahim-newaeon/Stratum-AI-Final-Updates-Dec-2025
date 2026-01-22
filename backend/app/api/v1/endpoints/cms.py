# =============================================================================
# Stratum AI - CMS (Content Management System) Endpoints
# =============================================================================
"""
CMS API endpoints for managing blog posts, pages, and contact submissions.

Public endpoints (no auth):
- GET /cms/posts - List published posts
- GET /cms/posts/{slug} - Get single post by slug
- GET /cms/categories - List active categories
- GET /cms/tags - List all tags
- POST /cms/contact - Submit contact form

Admin endpoints (superadmin only):
- CRUD for posts, pages, categories, tags, authors
- Contact submission management
"""

import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.cms import (
    CMSCategory,
    CMSTag,
    CMSAuthor,
    CMSPost,
    CMSPage,
    CMSContactSubmission,
    CMSPostStatus,
    CMSPageStatus,
    cms_post_tags,
)
from app.schemas.cms import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    TagCreate,
    TagUpdate,
    TagResponse,
    TagListResponse,
    AuthorCreate,
    AuthorUpdate,
    AuthorResponse,
    AuthorListResponse,
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    PostPublicResponse,
    PostPublicListResponse,
    PageCreate,
    PageUpdate,
    PageResponse,
    PageListResponse,
    ContactSubmit,
    ContactResponse,
    ContactListResponse,
    ContactMarkRead,
    ContactMarkResponded,
    ContactMarkSpam,
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/cms", tags=["CMS"])
logger = get_logger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def calculate_reading_time(content: Optional[str]) -> Optional[int]:
    """Estimate reading time based on word count (200 wpm average)."""
    if not content:
        return None
    words = len(re.findall(r"\w+", content))
    return max(1, round(words / 200))


def count_words(content: Optional[str]) -> Optional[int]:
    """Count words in content."""
    if not content:
        return None
    return len(re.findall(r"\w+", content))


async def check_superadmin(request: Request) -> bool:
    """Check if the current user is a superadmin."""
    user_role = getattr(request.state, "user_role", None)
    return user_role == "superadmin"


# =============================================================================
# Public Endpoints
# =============================================================================

@router.get("/posts", response_model=APIResponse[PostPublicListResponse])
async def list_published_posts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    category_slug: Optional[str] = None,
    tag_slug: Optional[str] = None,
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PostPublicListResponse]:
    """
    List published posts (public endpoint).
    Supports filtering by category, tag, content type, and search.
    """
    conditions = [
        CMSPost.status == CMSPostStatus.PUBLISHED.value,
        CMSPost.is_deleted == False,
    ]

    # Filter by category
    if category_slug:
        category_result = await db.execute(
            select(CMSCategory.id).where(CMSCategory.slug == category_slug)
        )
        category_id = category_result.scalar_one_or_none()
        if category_id:
            conditions.append(CMSPost.category_id == category_id)

    # Filter by content type
    if content_type:
        conditions.append(CMSPost.content_type == content_type)

    # Filter by featured
    if featured_only:
        conditions.append(CMSPost.is_featured == True)

    # Search in title and excerpt
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                CMSPost.title.ilike(search_pattern),
                CMSPost.excerpt.ilike(search_pattern),
            )
        )

    # Base query
    query = select(CMSPost).where(and_(*conditions))

    # Filter by tag (requires join)
    if tag_slug:
        tag_result = await db.execute(
            select(CMSTag.id).where(CMSTag.slug == tag_slug)
        )
        tag_id = tag_result.scalar_one_or_none()
        if tag_id:
            query = query.join(cms_post_tags).where(cms_post_tags.c.tag_id == tag_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch with pagination
    query = (
        query
        .options(selectinload(CMSPost.category), selectinload(CMSPost.author), selectinload(CMSPost.tags))
        .order_by(desc(CMSPost.published_at), desc(CMSPost.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    posts = result.scalars().unique().all()

    return APIResponse(
        success=True,
        data=PostPublicListResponse(
            posts=[
                PostPublicResponse(
                    id=p.id,
                    title=p.title,
                    slug=p.slug,
                    excerpt=p.excerpt,
                    content=p.content,
                    published_at=p.published_at,
                    meta_title=p.meta_title,
                    meta_description=p.meta_description,
                    og_image_url=p.og_image_url,
                    featured_image_url=p.featured_image_url,
                    featured_image_alt=p.featured_image_alt,
                    reading_time_minutes=p.reading_time_minutes,
                    view_count=p.view_count,
                    is_featured=p.is_featured,
                    content_type=p.content_type,
                    category=CategoryResponse(
                        id=p.category.id,
                        name=p.category.name,
                        slug=p.category.slug,
                        description=p.category.description,
                        color=p.category.color,
                        icon=p.category.icon,
                        display_order=p.category.display_order,
                        is_active=p.category.is_active,
                        created_at=p.category.created_at,
                        updated_at=p.category.updated_at,
                    ) if p.category else None,
                    author=AuthorResponse(
                        id=p.author.id,
                        user_id=p.author.user_id,
                        name=p.author.name,
                        slug=p.author.slug,
                        email=p.author.email,
                        bio=p.author.bio,
                        avatar_url=p.author.avatar_url,
                        job_title=p.author.job_title,
                        company=p.author.company,
                        twitter_handle=p.author.twitter_handle,
                        linkedin_url=p.author.linkedin_url,
                        github_handle=p.author.github_handle,
                        website_url=p.author.website_url,
                        is_active=p.author.is_active,
                        created_at=p.author.created_at,
                        updated_at=p.author.updated_at,
                    ) if p.author else None,
                    tags=[
                        TagResponse(
                            id=t.id,
                            name=t.name,
                            slug=t.slug,
                            description=t.description,
                            color=t.color,
                            usage_count=t.usage_count,
                            created_at=t.created_at,
                            updated_at=t.updated_at,
                        ) for t in p.tags
                    ],
                )
                for p in posts
            ],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/posts/{slug}", response_model=APIResponse[PostPublicResponse])
async def get_post_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PostPublicResponse]:
    """
    Get a single published post by slug (public endpoint).
    Increments view count.
    """
    result = await db.execute(
        select(CMSPost)
        .options(selectinload(CMSPost.category), selectinload(CMSPost.author), selectinload(CMSPost.tags))
        .where(
            and_(
                CMSPost.slug == slug,
                CMSPost.status == CMSPostStatus.PUBLISHED.value,
                CMSPost.is_deleted == False,
            )
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Increment view count
    post.view_count += 1
    await db.commit()

    return APIResponse(
        success=True,
        data=PostPublicResponse(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            content=post.content,
            published_at=post.published_at,
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            og_image_url=post.og_image_url,
            featured_image_url=post.featured_image_url,
            featured_image_alt=post.featured_image_alt,
            reading_time_minutes=post.reading_time_minutes,
            view_count=post.view_count,
            is_featured=post.is_featured,
            content_type=post.content_type,
            category=CategoryResponse(
                id=post.category.id,
                name=post.category.name,
                slug=post.category.slug,
                description=post.category.description,
                color=post.category.color,
                icon=post.category.icon,
                display_order=post.category.display_order,
                is_active=post.category.is_active,
                created_at=post.category.created_at,
                updated_at=post.category.updated_at,
            ) if post.category else None,
            author=AuthorResponse(
                id=post.author.id,
                user_id=post.author.user_id,
                name=post.author.name,
                slug=post.author.slug,
                email=post.author.email,
                bio=post.author.bio,
                avatar_url=post.author.avatar_url,
                job_title=post.author.job_title,
                company=post.author.company,
                twitter_handle=post.author.twitter_handle,
                linkedin_url=post.author.linkedin_url,
                github_handle=post.author.github_handle,
                website_url=post.author.website_url,
                is_active=post.author.is_active,
                created_at=post.author.created_at,
                updated_at=post.author.updated_at,
            ) if post.author else None,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description,
                    color=t.color,
                    usage_count=t.usage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                ) for t in post.tags
            ],
        ),
    )


@router.get("/categories", response_model=APIResponse[CategoryListResponse])
async def list_categories(
    active_only: bool = True,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[CategoryListResponse]:
    """List categories (public endpoint)."""
    conditions = []
    if active_only:
        conditions.append(CMSCategory.is_active == True)

    query = select(CMSCategory)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(CMSCategory.display_order, CMSCategory.name)

    result = await db.execute(query)
    categories = result.scalars().all()

    return APIResponse(
        success=True,
        data=CategoryListResponse(
            categories=[
                CategoryResponse(
                    id=c.id,
                    name=c.name,
                    slug=c.slug,
                    description=c.description,
                    color=c.color,
                    icon=c.icon,
                    display_order=c.display_order,
                    is_active=c.is_active,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in categories
            ],
            total=len(categories),
        ),
    )


@router.get("/tags", response_model=APIResponse[TagListResponse])
async def list_tags(
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[TagListResponse]:
    """List all tags (public endpoint)."""
    result = await db.execute(
        select(CMSTag).order_by(desc(CMSTag.usage_count), CMSTag.name)
    )
    tags = result.scalars().all()

    return APIResponse(
        success=True,
        data=TagListResponse(
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description,
                    color=t.color,
                    usage_count=t.usage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tags
            ],
            total=len(tags),
        ),
    )


@router.post("/contact", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def submit_contact_form(
    request: Request,
    body: ContactSubmit,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[dict]:
    """
    Submit contact form (public endpoint).
    """
    # Get IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:512]

    submission = CMSContactSubmission(
        name=body.name,
        email=body.email,
        company=body.company,
        phone=body.phone,
        subject=body.subject,
        message=body.message,
        source_page=body.source_page,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(submission)
    await db.commit()

    logger.info(f"Contact form submitted: {body.email}")

    return APIResponse(
        success=True,
        data={"submitted": True},
        message="Thank you for your message. We'll get back to you soon!",
    )


# =============================================================================
# Admin Endpoints - Posts
# =============================================================================

@router.get("/admin/posts", response_model=APIResponse[PostListResponse])
async def admin_list_posts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PostListResponse]:
    """List all posts (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    conditions = [CMSPost.is_deleted == False]

    if status_filter:
        conditions.append(CMSPost.status == status_filter)

    if content_type:
        conditions.append(CMSPost.content_type == content_type)

    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                CMSPost.title.ilike(search_pattern),
                CMSPost.excerpt.ilike(search_pattern),
            )
        )

    # Count total
    count_query = select(func.count(CMSPost.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch posts
    query = (
        select(CMSPost)
        .options(selectinload(CMSPost.category), selectinload(CMSPost.author), selectinload(CMSPost.tags))
        .where(and_(*conditions))
        .order_by(desc(CMSPost.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    posts = result.scalars().unique().all()

    return APIResponse(
        success=True,
        data=PostListResponse(
            posts=[
                PostResponse(
                    id=p.id,
                    title=p.title,
                    slug=p.slug,
                    excerpt=p.excerpt,
                    content=p.content,
                    content_json=p.content_json,
                    status=p.status,
                    content_type=p.content_type,
                    published_at=p.published_at,
                    scheduled_at=p.scheduled_at,
                    meta_title=p.meta_title,
                    meta_description=p.meta_description,
                    canonical_url=p.canonical_url,
                    og_image_url=p.og_image_url,
                    featured_image_url=p.featured_image_url,
                    featured_image_alt=p.featured_image_alt,
                    reading_time_minutes=p.reading_time_minutes,
                    word_count=p.word_count,
                    view_count=p.view_count,
                    is_featured=p.is_featured,
                    allow_comments=p.allow_comments,
                    category=CategoryResponse(
                        id=p.category.id,
                        name=p.category.name,
                        slug=p.category.slug,
                        description=p.category.description,
                        color=p.category.color,
                        icon=p.category.icon,
                        display_order=p.category.display_order,
                        is_active=p.category.is_active,
                        created_at=p.category.created_at,
                        updated_at=p.category.updated_at,
                    ) if p.category else None,
                    author=AuthorResponse(
                        id=p.author.id,
                        user_id=p.author.user_id,
                        name=p.author.name,
                        slug=p.author.slug,
                        email=p.author.email,
                        bio=p.author.bio,
                        avatar_url=p.author.avatar_url,
                        job_title=p.author.job_title,
                        company=p.author.company,
                        twitter_handle=p.author.twitter_handle,
                        linkedin_url=p.author.linkedin_url,
                        github_handle=p.author.github_handle,
                        website_url=p.author.website_url,
                        is_active=p.author.is_active,
                        created_at=p.author.created_at,
                        updated_at=p.author.updated_at,
                    ) if p.author else None,
                    tags=[
                        TagResponse(
                            id=t.id,
                            name=t.name,
                            slug=t.slug,
                            description=t.description,
                            color=t.color,
                            usage_count=t.usage_count,
                            created_at=t.created_at,
                            updated_at=t.updated_at,
                        ) for t in p.tags
                    ],
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
                for p in posts
            ],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/admin/posts/{post_id}", response_model=APIResponse[PostResponse])
async def admin_get_post(
    request: Request,
    post_id: UUID,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PostResponse]:
    """Get a single post by ID (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSPost)
        .options(selectinload(CMSPost.category), selectinload(CMSPost.author), selectinload(CMSPost.tags))
        .where(and_(CMSPost.id == post_id, CMSPost.is_deleted == False))
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    return APIResponse(
        success=True,
        data=PostResponse(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            content=post.content,
            content_json=post.content_json,
            status=post.status,
            content_type=post.content_type,
            published_at=post.published_at,
            scheduled_at=post.scheduled_at,
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            canonical_url=post.canonical_url,
            og_image_url=post.og_image_url,
            featured_image_url=post.featured_image_url,
            featured_image_alt=post.featured_image_alt,
            reading_time_minutes=post.reading_time_minutes,
            word_count=post.word_count,
            view_count=post.view_count,
            is_featured=post.is_featured,
            allow_comments=post.allow_comments,
            category=CategoryResponse(
                id=post.category.id,
                name=post.category.name,
                slug=post.category.slug,
                description=post.category.description,
                color=post.category.color,
                icon=post.category.icon,
                display_order=post.category.display_order,
                is_active=post.category.is_active,
                created_at=post.category.created_at,
                updated_at=post.category.updated_at,
            ) if post.category else None,
            author=AuthorResponse(
                id=post.author.id,
                user_id=post.author.user_id,
                name=post.author.name,
                slug=post.author.slug,
                email=post.author.email,
                bio=post.author.bio,
                avatar_url=post.author.avatar_url,
                job_title=post.author.job_title,
                company=post.author.company,
                twitter_handle=post.author.twitter_handle,
                linkedin_url=post.author.linkedin_url,
                github_handle=post.author.github_handle,
                website_url=post.author.website_url,
                is_active=post.author.is_active,
                created_at=post.author.created_at,
                updated_at=post.author.updated_at,
            ) if post.author else None,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description,
                    color=t.color,
                    usage_count=t.usage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                ) for t in post.tags
            ],
            created_at=post.created_at,
            updated_at=post.updated_at,
        ),
    )


@router.post("/admin/posts", response_model=APIResponse[PostResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_post(
    request: Request,
    body: PostCreate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PostResponse]:
    """Create a new post (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    # Generate slug if not provided
    slug = body.slug or slugify(body.title)

    # Check slug uniqueness
    existing = await db.execute(select(CMSPost.id).where(CMSPost.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Calculate reading time and word count
    reading_time = body.reading_time_minutes or calculate_reading_time(body.content)
    word_count = count_words(body.content)

    post = CMSPost(
        title=body.title,
        slug=slug,
        excerpt=body.excerpt,
        content=body.content,
        content_json=body.content_json,
        status=body.status,
        content_type=body.content_type,
        category_id=body.category_id,
        author_id=body.author_id,
        published_at=body.published_at if body.status == "published" else None,
        scheduled_at=body.scheduled_at,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        canonical_url=body.canonical_url,
        og_image_url=body.og_image_url,
        featured_image_url=body.featured_image_url,
        featured_image_alt=body.featured_image_alt,
        reading_time_minutes=reading_time,
        word_count=word_count,
        is_featured=body.is_featured,
        allow_comments=body.allow_comments,
    )

    db.add(post)
    await db.flush()

    # Add tags
    if body.tag_ids:
        tag_result = await db.execute(
            select(CMSTag).where(CMSTag.id.in_(body.tag_ids))
        )
        tags = tag_result.scalars().all()
        post.tags = list(tags)

        # Update tag usage counts
        for tag in tags:
            tag.usage_count += 1

    await db.commit()
    await db.refresh(post)

    # Reload with relationships
    result = await db.execute(
        select(CMSPost)
        .options(selectinload(CMSPost.category), selectinload(CMSPost.author), selectinload(CMSPost.tags))
        .where(CMSPost.id == post.id)
    )
    post = result.scalar_one()

    logger.info(f"Post created: {post.id} - {post.title}")

    return APIResponse(
        success=True,
        data=PostResponse(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            content=post.content,
            content_json=post.content_json,
            status=post.status,
            content_type=post.content_type,
            published_at=post.published_at,
            scheduled_at=post.scheduled_at,
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            canonical_url=post.canonical_url,
            og_image_url=post.og_image_url,
            featured_image_url=post.featured_image_url,
            featured_image_alt=post.featured_image_alt,
            reading_time_minutes=post.reading_time_minutes,
            word_count=post.word_count,
            view_count=post.view_count,
            is_featured=post.is_featured,
            allow_comments=post.allow_comments,
            category=CategoryResponse(
                id=post.category.id,
                name=post.category.name,
                slug=post.category.slug,
                description=post.category.description,
                color=post.category.color,
                icon=post.category.icon,
                display_order=post.category.display_order,
                is_active=post.category.is_active,
                created_at=post.category.created_at,
                updated_at=post.category.updated_at,
            ) if post.category else None,
            author=AuthorResponse(
                id=post.author.id,
                user_id=post.author.user_id,
                name=post.author.name,
                slug=post.author.slug,
                email=post.author.email,
                bio=post.author.bio,
                avatar_url=post.author.avatar_url,
                job_title=post.author.job_title,
                company=post.author.company,
                twitter_handle=post.author.twitter_handle,
                linkedin_url=post.author.linkedin_url,
                github_handle=post.author.github_handle,
                website_url=post.author.website_url,
                is_active=post.author.is_active,
                created_at=post.author.created_at,
                updated_at=post.author.updated_at,
            ) if post.author else None,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description,
                    color=t.color,
                    usage_count=t.usage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                ) for t in post.tags
            ],
            created_at=post.created_at,
            updated_at=post.updated_at,
        ),
    )


@router.patch("/admin/posts/{post_id}", response_model=APIResponse[PostResponse])
async def admin_update_post(
    request: Request,
    post_id: UUID,
    body: PostUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PostResponse]:
    """Update a post (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSPost)
        .options(selectinload(CMSPost.tags))
        .where(and_(CMSPost.id == post_id, CMSPost.is_deleted == False))
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Update fields
    if body.title is not None:
        post.title = body.title
    if body.slug is not None:
        post.slug = body.slug
    if body.excerpt is not None:
        post.excerpt = body.excerpt
    if body.content is not None:
        post.content = body.content
        post.reading_time_minutes = calculate_reading_time(body.content)
        post.word_count = count_words(body.content)
    if body.content_json is not None:
        post.content_json = body.content_json
    if body.status is not None:
        was_published = post.status == CMSPostStatus.PUBLISHED.value
        post.status = body.status
        if body.status == "published" and not was_published:
            post.published_at = datetime.now(timezone.utc)
    if body.content_type is not None:
        post.content_type = body.content_type
    if body.category_id is not None:
        post.category_id = body.category_id
    if body.author_id is not None:
        post.author_id = body.author_id
    if body.published_at is not None:
        post.published_at = body.published_at
    if body.scheduled_at is not None:
        post.scheduled_at = body.scheduled_at
    if body.meta_title is not None:
        post.meta_title = body.meta_title
    if body.meta_description is not None:
        post.meta_description = body.meta_description
    if body.canonical_url is not None:
        post.canonical_url = body.canonical_url
    if body.og_image_url is not None:
        post.og_image_url = body.og_image_url
    if body.featured_image_url is not None:
        post.featured_image_url = body.featured_image_url
    if body.featured_image_alt is not None:
        post.featured_image_alt = body.featured_image_alt
    if body.reading_time_minutes is not None:
        post.reading_time_minutes = body.reading_time_minutes
    if body.is_featured is not None:
        post.is_featured = body.is_featured
    if body.allow_comments is not None:
        post.allow_comments = body.allow_comments

    # Update tags
    if body.tag_ids is not None:
        # Decrement old tag counts
        for tag in post.tags:
            tag.usage_count = max(0, tag.usage_count - 1)

        # Get new tags
        tag_result = await db.execute(
            select(CMSTag).where(CMSTag.id.in_(body.tag_ids))
        )
        new_tags = tag_result.scalars().all()
        post.tags = list(new_tags)

        # Increment new tag counts
        for tag in new_tags:
            tag.usage_count += 1

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(CMSPost)
        .options(selectinload(CMSPost.category), selectinload(CMSPost.author), selectinload(CMSPost.tags))
        .where(CMSPost.id == post.id)
    )
    post = result.scalar_one()

    return APIResponse(
        success=True,
        data=PostResponse(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            content=post.content,
            content_json=post.content_json,
            status=post.status,
            content_type=post.content_type,
            published_at=post.published_at,
            scheduled_at=post.scheduled_at,
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            canonical_url=post.canonical_url,
            og_image_url=post.og_image_url,
            featured_image_url=post.featured_image_url,
            featured_image_alt=post.featured_image_alt,
            reading_time_minutes=post.reading_time_minutes,
            word_count=post.word_count,
            view_count=post.view_count,
            is_featured=post.is_featured,
            allow_comments=post.allow_comments,
            category=CategoryResponse(
                id=post.category.id,
                name=post.category.name,
                slug=post.category.slug,
                description=post.category.description,
                color=post.category.color,
                icon=post.category.icon,
                display_order=post.category.display_order,
                is_active=post.category.is_active,
                created_at=post.category.created_at,
                updated_at=post.category.updated_at,
            ) if post.category else None,
            author=AuthorResponse(
                id=post.author.id,
                user_id=post.author.user_id,
                name=post.author.name,
                slug=post.author.slug,
                email=post.author.email,
                bio=post.author.bio,
                avatar_url=post.author.avatar_url,
                job_title=post.author.job_title,
                company=post.author.company,
                twitter_handle=post.author.twitter_handle,
                linkedin_url=post.author.linkedin_url,
                github_handle=post.author.github_handle,
                website_url=post.author.website_url,
                is_active=post.author.is_active,
                created_at=post.author.created_at,
                updated_at=post.author.updated_at,
            ) if post.author else None,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description,
                    color=t.color,
                    usage_count=t.usage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                ) for t in post.tags
            ],
            created_at=post.created_at,
            updated_at=post.updated_at,
        ),
    )


@router.delete("/admin/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_post(
    request: Request,
    post_id: UUID,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Soft delete a post (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSPost).where(and_(CMSPost.id == post_id, CMSPost.is_deleted == False))
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.soft_delete()
    await db.commit()

    logger.info(f"Post deleted: {post_id}")


# =============================================================================
# Admin Endpoints - Categories
# =============================================================================

@router.get("/admin/categories", response_model=APIResponse[CategoryListResponse])
async def admin_list_categories(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[CategoryListResponse]:
    """List all categories (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSCategory).order_by(CMSCategory.display_order, CMSCategory.name)
    )
    categories = result.scalars().all()

    return APIResponse(
        success=True,
        data=CategoryListResponse(
            categories=[
                CategoryResponse(
                    id=c.id,
                    name=c.name,
                    slug=c.slug,
                    description=c.description,
                    color=c.color,
                    icon=c.icon,
                    display_order=c.display_order,
                    is_active=c.is_active,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in categories
            ],
            total=len(categories),
        ),
    )


@router.post("/admin/categories", response_model=APIResponse[CategoryResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_category(
    request: Request,
    body: CategoryCreate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[CategoryResponse]:
    """Create a category (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    slug = body.slug or slugify(body.name)

    category = CMSCategory(
        name=body.name,
        slug=slug,
        description=body.description,
        color=body.color,
        icon=body.icon,
        display_order=body.display_order,
        is_active=body.is_active,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return APIResponse(
        success=True,
        data=CategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            color=category.color,
            icon=category.icon,
            display_order=category.display_order,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
        ),
    )


@router.patch("/admin/categories/{category_id}", response_model=APIResponse[CategoryResponse])
async def admin_update_category(
    request: Request,
    category_id: UUID,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[CategoryResponse]:
    """Update a category (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSCategory).where(CMSCategory.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if body.name is not None:
        category.name = body.name
    if body.slug is not None:
        category.slug = body.slug
    if body.description is not None:
        category.description = body.description
    if body.color is not None:
        category.color = body.color
    if body.icon is not None:
        category.icon = body.icon
    if body.display_order is not None:
        category.display_order = body.display_order
    if body.is_active is not None:
        category.is_active = body.is_active

    await db.commit()
    await db.refresh(category)

    return APIResponse(
        success=True,
        data=CategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            color=category.color,
            icon=category.icon,
            display_order=category.display_order,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
        ),
    )


@router.delete("/admin/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_category(
    request: Request,
    category_id: UUID,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a category (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSCategory).where(CMSCategory.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    await db.delete(category)
    await db.commit()


# =============================================================================
# Admin Endpoints - Tags
# =============================================================================

@router.get("/admin/tags", response_model=APIResponse[TagListResponse])
async def admin_list_tags(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[TagListResponse]:
    """List all tags (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSTag).order_by(desc(CMSTag.usage_count), CMSTag.name)
    )
    tags = result.scalars().all()

    return APIResponse(
        success=True,
        data=TagListResponse(
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description,
                    color=t.color,
                    usage_count=t.usage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tags
            ],
            total=len(tags),
        ),
    )


@router.post("/admin/tags", response_model=APIResponse[TagResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_tag(
    request: Request,
    body: TagCreate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[TagResponse]:
    """Create a tag (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    slug = body.slug or slugify(body.name)

    tag = CMSTag(
        name=body.name,
        slug=slug,
        description=body.description,
        color=body.color,
    )

    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return APIResponse(
        success=True,
        data=TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            description=tag.description,
            color=tag.color,
            usage_count=tag.usage_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        ),
    )


@router.patch("/admin/tags/{tag_id}", response_model=APIResponse[TagResponse])
async def admin_update_tag(
    request: Request,
    tag_id: UUID,
    body: TagUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[TagResponse]:
    """Update a tag (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSTag).where(CMSTag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    if body.name is not None:
        tag.name = body.name
    if body.slug is not None:
        tag.slug = body.slug
    if body.description is not None:
        tag.description = body.description
    if body.color is not None:
        tag.color = body.color

    await db.commit()
    await db.refresh(tag)

    return APIResponse(
        success=True,
        data=TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            description=tag.description,
            color=tag.color,
            usage_count=tag.usage_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        ),
    )


@router.delete("/admin/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_tag(
    request: Request,
    tag_id: UUID,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a tag (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSTag).where(CMSTag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    await db.delete(tag)
    await db.commit()


# =============================================================================
# Admin Endpoints - Authors
# =============================================================================

@router.get("/admin/authors", response_model=APIResponse[AuthorListResponse])
async def admin_list_authors(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[AuthorListResponse]:
    """List all authors (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSAuthor).order_by(CMSAuthor.name))
    authors = result.scalars().all()

    return APIResponse(
        success=True,
        data=AuthorListResponse(
            authors=[
                AuthorResponse(
                    id=a.id,
                    user_id=a.user_id,
                    name=a.name,
                    slug=a.slug,
                    email=a.email,
                    bio=a.bio,
                    avatar_url=a.avatar_url,
                    job_title=a.job_title,
                    company=a.company,
                    twitter_handle=a.twitter_handle,
                    linkedin_url=a.linkedin_url,
                    github_handle=a.github_handle,
                    website_url=a.website_url,
                    is_active=a.is_active,
                    created_at=a.created_at,
                    updated_at=a.updated_at,
                )
                for a in authors
            ],
            total=len(authors),
        ),
    )


@router.post("/admin/authors", response_model=APIResponse[AuthorResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_author(
    request: Request,
    body: AuthorCreate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[AuthorResponse]:
    """Create an author (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    slug = body.slug or slugify(body.name)

    author = CMSAuthor(
        user_id=body.user_id,
        name=body.name,
        slug=slug,
        email=body.email,
        bio=body.bio,
        avatar_url=body.avatar_url,
        job_title=body.job_title,
        company=body.company,
        twitter_handle=body.twitter_handle,
        linkedin_url=body.linkedin_url,
        github_handle=body.github_handle,
        website_url=body.website_url,
        is_active=body.is_active,
    )

    db.add(author)
    await db.commit()
    await db.refresh(author)

    return APIResponse(
        success=True,
        data=AuthorResponse(
            id=author.id,
            user_id=author.user_id,
            name=author.name,
            slug=author.slug,
            email=author.email,
            bio=author.bio,
            avatar_url=author.avatar_url,
            job_title=author.job_title,
            company=author.company,
            twitter_handle=author.twitter_handle,
            linkedin_url=author.linkedin_url,
            github_handle=author.github_handle,
            website_url=author.website_url,
            is_active=author.is_active,
            created_at=author.created_at,
            updated_at=author.updated_at,
        ),
    )


@router.patch("/admin/authors/{author_id}", response_model=APIResponse[AuthorResponse])
async def admin_update_author(
    request: Request,
    author_id: UUID,
    body: AuthorUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[AuthorResponse]:
    """Update an author (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSAuthor).where(CMSAuthor.id == author_id))
    author = result.scalar_one_or_none()

    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    if body.name is not None:
        author.name = body.name
    if body.slug is not None:
        author.slug = body.slug
    if body.email is not None:
        author.email = body.email
    if body.bio is not None:
        author.bio = body.bio
    if body.avatar_url is not None:
        author.avatar_url = body.avatar_url
    if body.job_title is not None:
        author.job_title = body.job_title
    if body.company is not None:
        author.company = body.company
    if body.twitter_handle is not None:
        author.twitter_handle = body.twitter_handle
    if body.linkedin_url is not None:
        author.linkedin_url = body.linkedin_url
    if body.github_handle is not None:
        author.github_handle = body.github_handle
    if body.website_url is not None:
        author.website_url = body.website_url
    if body.user_id is not None:
        author.user_id = body.user_id
    if body.is_active is not None:
        author.is_active = body.is_active

    await db.commit()
    await db.refresh(author)

    return APIResponse(
        success=True,
        data=AuthorResponse(
            id=author.id,
            user_id=author.user_id,
            name=author.name,
            slug=author.slug,
            email=author.email,
            bio=author.bio,
            avatar_url=author.avatar_url,
            job_title=author.job_title,
            company=author.company,
            twitter_handle=author.twitter_handle,
            linkedin_url=author.linkedin_url,
            github_handle=author.github_handle,
            website_url=author.website_url,
            is_active=author.is_active,
            created_at=author.created_at,
            updated_at=author.updated_at,
        ),
    )


@router.delete("/admin/authors/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_author(
    request: Request,
    author_id: UUID,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete an author (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(select(CMSAuthor).where(CMSAuthor.id == author_id))
    author = result.scalar_one_or_none()

    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    await db.delete(author)
    await db.commit()


# =============================================================================
# Admin Endpoints - Pages
# =============================================================================

@router.get("/admin/pages", response_model=APIResponse[PageListResponse])
async def admin_list_pages(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PageListResponse]:
    """List all pages (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSPage)
        .where(CMSPage.is_deleted == False)
        .order_by(CMSPage.navigation_order, CMSPage.title)
    )
    pages = result.scalars().all()

    return APIResponse(
        success=True,
        data=PageListResponse(
            pages=[
                PageResponse(
                    id=p.id,
                    title=p.title,
                    slug=p.slug,
                    content=p.content,
                    content_json=p.content_json,
                    status=p.status,
                    published_at=p.published_at,
                    meta_title=p.meta_title,
                    meta_description=p.meta_description,
                    show_in_navigation=p.show_in_navigation,
                    navigation_label=p.navigation_label,
                    navigation_order=p.navigation_order,
                    template=p.template,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
                for p in pages
            ],
            total=len(pages),
        ),
    )


@router.post("/admin/pages", response_model=APIResponse[PageResponse], status_code=status.HTTP_201_CREATED)
async def admin_create_page(
    request: Request,
    body: PageCreate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PageResponse]:
    """Create a page (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    slug = body.slug or slugify(body.title)

    page = CMSPage(
        title=body.title,
        slug=slug,
        content=body.content,
        content_json=body.content_json,
        status=body.status,
        published_at=datetime.now(timezone.utc) if body.status == "published" else None,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        show_in_navigation=body.show_in_navigation,
        navigation_label=body.navigation_label,
        navigation_order=body.navigation_order,
        template=body.template,
    )

    db.add(page)
    await db.commit()
    await db.refresh(page)

    return APIResponse(
        success=True,
        data=PageResponse(
            id=page.id,
            title=page.title,
            slug=page.slug,
            content=page.content,
            content_json=page.content_json,
            status=page.status,
            published_at=page.published_at,
            meta_title=page.meta_title,
            meta_description=page.meta_description,
            show_in_navigation=page.show_in_navigation,
            navigation_label=page.navigation_label,
            navigation_order=page.navigation_order,
            template=page.template,
            created_at=page.created_at,
            updated_at=page.updated_at,
        ),
    )


@router.patch("/admin/pages/{page_id}", response_model=APIResponse[PageResponse])
async def admin_update_page(
    request: Request,
    page_id: UUID,
    body: PageUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[PageResponse]:
    """Update a page (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSPage).where(and_(CMSPage.id == page_id, CMSPage.is_deleted == False))
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    if body.title is not None:
        page.title = body.title
    if body.slug is not None:
        page.slug = body.slug
    if body.content is not None:
        page.content = body.content
    if body.content_json is not None:
        page.content_json = body.content_json
    if body.status is not None:
        was_published = page.status == CMSPageStatus.PUBLISHED.value
        page.status = body.status
        if body.status == "published" and not was_published:
            page.published_at = datetime.now(timezone.utc)
    if body.meta_title is not None:
        page.meta_title = body.meta_title
    if body.meta_description is not None:
        page.meta_description = body.meta_description
    if body.show_in_navigation is not None:
        page.show_in_navigation = body.show_in_navigation
    if body.navigation_label is not None:
        page.navigation_label = body.navigation_label
    if body.navigation_order is not None:
        page.navigation_order = body.navigation_order
    if body.template is not None:
        page.template = body.template

    await db.commit()
    await db.refresh(page)

    return APIResponse(
        success=True,
        data=PageResponse(
            id=page.id,
            title=page.title,
            slug=page.slug,
            content=page.content,
            content_json=page.content_json,
            status=page.status,
            published_at=page.published_at,
            meta_title=page.meta_title,
            meta_description=page.meta_description,
            show_in_navigation=page.show_in_navigation,
            navigation_label=page.navigation_label,
            navigation_order=page.navigation_order,
            template=page.template,
            created_at=page.created_at,
            updated_at=page.updated_at,
        ),
    )


@router.delete("/admin/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_page(
    request: Request,
    page_id: UUID,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Soft delete a page (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSPage).where(and_(CMSPage.id == page_id, CMSPage.is_deleted == False))
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    page.soft_delete()
    await db.commit()


# =============================================================================
# Admin Endpoints - Contact Submissions
# =============================================================================

@router.get("/admin/contacts", response_model=APIResponse[ContactListResponse])
async def admin_list_contacts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    exclude_spam: bool = True,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ContactListResponse]:
    """List contact submissions (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    conditions = []

    if unread_only:
        conditions.append(CMSContactSubmission.is_read == False)

    if exclude_spam:
        conditions.append(CMSContactSubmission.is_spam == False)

    # Count total
    count_query = select(func.count(CMSContactSubmission.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch
    query = select(CMSContactSubmission)
    if conditions:
        query = query.where(and_(*conditions))
    query = (
        query
        .order_by(desc(CMSContactSubmission.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    contacts = result.scalars().all()

    return APIResponse(
        success=True,
        data=ContactListResponse(
            contacts=[
                ContactResponse(
                    id=c.id,
                    name=c.name,
                    email=c.email,
                    company=c.company,
                    phone=c.phone,
                    subject=c.subject,
                    message=c.message,
                    source_page=c.source_page,
                    is_read=c.is_read,
                    read_at=c.read_at,
                    is_responded=c.is_responded,
                    responded_at=c.responded_at,
                    response_notes=c.response_notes,
                    is_spam=c.is_spam,
                    created_at=c.created_at,
                )
                for c in contacts
            ],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.patch("/admin/contacts/{contact_id}/read", response_model=APIResponse[ContactResponse])
async def admin_mark_contact_read(
    request: Request,
    contact_id: UUID,
    body: ContactMarkRead,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ContactResponse]:
    """Mark contact as read (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    user_id = getattr(request.state, "user_id", None)

    result = await db.execute(
        select(CMSContactSubmission).where(CMSContactSubmission.id == contact_id)
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.is_read = body.is_read
    if body.is_read:
        contact.read_at = datetime.now(timezone.utc)
        contact.read_by_user_id = user_id
    else:
        contact.read_at = None
        contact.read_by_user_id = None

    await db.commit()
    await db.refresh(contact)

    return APIResponse(
        success=True,
        data=ContactResponse(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            company=contact.company,
            phone=contact.phone,
            subject=contact.subject,
            message=contact.message,
            source_page=contact.source_page,
            is_read=contact.is_read,
            read_at=contact.read_at,
            is_responded=contact.is_responded,
            responded_at=contact.responded_at,
            response_notes=contact.response_notes,
            is_spam=contact.is_spam,
            created_at=contact.created_at,
        ),
    )


@router.patch("/admin/contacts/{contact_id}/responded", response_model=APIResponse[ContactResponse])
async def admin_mark_contact_responded(
    request: Request,
    contact_id: UUID,
    body: ContactMarkResponded,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ContactResponse]:
    """Mark contact as responded (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSContactSubmission).where(CMSContactSubmission.id == contact_id)
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.is_responded = body.is_responded
    if body.is_responded:
        contact.responded_at = datetime.now(timezone.utc)
    else:
        contact.responded_at = None

    if body.response_notes is not None:
        contact.response_notes = body.response_notes

    await db.commit()
    await db.refresh(contact)

    return APIResponse(
        success=True,
        data=ContactResponse(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            company=contact.company,
            phone=contact.phone,
            subject=contact.subject,
            message=contact.message,
            source_page=contact.source_page,
            is_read=contact.is_read,
            read_at=contact.read_at,
            is_responded=contact.is_responded,
            responded_at=contact.responded_at,
            response_notes=contact.response_notes,
            is_spam=contact.is_spam,
            created_at=contact.created_at,
        ),
    )


@router.patch("/admin/contacts/{contact_id}/spam", response_model=APIResponse[ContactResponse])
async def admin_mark_contact_spam(
    request: Request,
    contact_id: UUID,
    body: ContactMarkSpam,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[ContactResponse]:
    """Mark contact as spam (admin endpoint)."""
    if not await check_superadmin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")

    result = await db.execute(
        select(CMSContactSubmission).where(CMSContactSubmission.id == contact_id)
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.is_spam = body.is_spam

    await db.commit()
    await db.refresh(contact)

    return APIResponse(
        success=True,
        data=ContactResponse(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            company=contact.company,
            phone=contact.phone,
            subject=contact.subject,
            message=contact.message,
            source_page=contact.source_page,
            is_read=contact.is_read,
            read_at=contact.read_at,
            is_responded=contact.is_responded,
            responded_at=contact.responded_at,
            response_notes=contact.response_notes,
            is_spam=contact.is_spam,
            created_at=contact.created_at,
        ),
    )
