# =============================================================================
# Stratum AI - CMS Pydantic Schemas
# =============================================================================
"""
Pydantic schemas for CMS API request/response validation.

Schemas:
- Category management
- Tag management
- Author management
- Post management
- Page management
- Contact form submissions
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Base Configuration
# =============================================================================


class CMSBaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# =============================================================================
# Category Schemas
# =============================================================================


class CategoryCreate(BaseModel):
    """Create a new category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    slug: Optional[str] = Field(
        None, max_length=100, description="URL-friendly slug (auto-generated if not provided)"
    )
    description: Optional[str] = Field(None, description="Category description")
    color: Optional[str] = Field(
        None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code"
    )
    icon: Optional[str] = Field(None, max_length=50, description="Icon name")
    display_order: int = Field(0, ge=0, description="Display order")
    is_active: bool = Field(True, description="Whether category is active")


class CategoryUpdate(BaseModel):
    """Update a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CategoryResponse(CMSBaseSchema):
    """Category in API responses."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    """List of categories."""

    categories: list[CategoryResponse]
    total: int


# =============================================================================
# Tag Schemas
# =============================================================================


class TagCreate(BaseModel):
    """Create a new tag."""

    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    slug: Optional[str] = Field(None, max_length=50, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagUpdate(BaseModel):
    """Update a tag."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(CMSBaseSchema):
    """Tag in API responses."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    usage_count: int
    created_at: datetime
    updated_at: datetime


class TagListResponse(BaseModel):
    """List of tags."""

    tags: list[TagResponse]
    total: int


# =============================================================================
# Author Schemas
# =============================================================================


class AuthorCreate(BaseModel):
    """Create a new author."""

    name: str = Field(..., min_length=1, max_length=255, description="Author name")
    slug: Optional[str] = Field(None, max_length=100, description="URL-friendly slug")
    email: Optional[str] = Field(None, max_length=255, description="Author email")
    bio: Optional[str] = Field(None, description="Author biography")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar image URL")
    job_title: Optional[str] = Field(None, max_length=100, description="Job title")
    company: Optional[str] = Field(None, max_length=100, description="Company name")
    twitter_handle: Optional[str] = Field(
        None, max_length=50, description="Twitter handle without @"
    )
    linkedin_url: Optional[str] = Field(None, max_length=255, description="LinkedIn profile URL")
    github_handle: Optional[str] = Field(None, max_length=50, description="GitHub username")
    website_url: Optional[str] = Field(None, max_length=255, description="Personal website URL")
    user_id: Optional[int] = Field(None, description="Link to user account")
    is_active: bool = Field(True, description="Whether author is active")


class AuthorUpdate(BaseModel):
    """Update an author."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(None, max_length=500)
    job_title: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    twitter_handle: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    github_handle: Optional[str] = Field(None, max_length=50)
    website_url: Optional[str] = Field(None, max_length=255)
    user_id: Optional[int] = None
    is_active: Optional[bool] = None


class AuthorResponse(CMSBaseSchema):
    """Author in API responses."""

    id: UUID
    user_id: Optional[int] = None
    name: str
    slug: str
    email: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    twitter_handle: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_handle: Optional[str] = None
    website_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthorListResponse(BaseModel):
    """List of authors."""

    authors: list[AuthorResponse]
    total: int


# =============================================================================
# Post Schemas
# =============================================================================


class PostCreate(BaseModel):
    """Create a new post."""

    title: str = Field(..., min_length=1, max_length=255, description="Post title")
    slug: Optional[str] = Field(None, max_length=255, description="URL-friendly slug")
    excerpt: Optional[str] = Field(None, description="Short description/excerpt")
    content: Optional[str] = Field(None, description="HTML content")
    content_json: Optional[dict[str, Any]] = Field(None, description="TipTap JSON content")
    status: str = Field("draft", description="Post status: draft, scheduled, published, archived")
    content_type: str = Field(
        "blog_post",
        description="Content type: blog_post, case_study, guide, whitepaper, announcement",
    )
    category_id: Optional[UUID] = Field(None, description="Category ID")
    author_id: Optional[UUID] = Field(None, description="Author ID")
    tag_ids: Optional[list[UUID]] = Field(default_factory=list, description="List of tag IDs")
    published_at: Optional[datetime] = Field(None, description="Publish date")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule date for publishing")
    meta_title: Optional[str] = Field(None, max_length=70, description="SEO title")
    meta_description: Optional[str] = Field(None, max_length=160, description="SEO description")
    canonical_url: Optional[str] = Field(None, max_length=500, description="Canonical URL")
    og_image_url: Optional[str] = Field(None, max_length=500, description="Open Graph image URL")
    featured_image_url: Optional[str] = Field(
        None, max_length=500, description="Featured image URL"
    )
    featured_image_alt: Optional[str] = Field(
        None, max_length=255, description="Featured image alt text"
    )
    reading_time_minutes: Optional[int] = Field(None, ge=1, description="Estimated reading time")
    is_featured: bool = Field(False, description="Whether post is featured")
    allow_comments: bool = Field(True, description="Whether comments are allowed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"draft", "scheduled", "published", "archived"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return v.lower()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = {"blog_post", "case_study", "guide", "whitepaper", "announcement"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid content type. Allowed: {allowed}")
        return v.lower()


class PostUpdate(BaseModel):
    """Update a post."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    excerpt: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    status: Optional[str] = None
    content_type: Optional[str] = None
    category_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    tag_ids: Optional[list[UUID]] = None
    published_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    canonical_url: Optional[str] = Field(None, max_length=500)
    og_image_url: Optional[str] = Field(None, max_length=500)
    featured_image_url: Optional[str] = Field(None, max_length=500)
    featured_image_alt: Optional[str] = Field(None, max_length=255)
    reading_time_minutes: Optional[int] = Field(None, ge=1)
    is_featured: Optional[bool] = None
    allow_comments: Optional[bool] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"draft", "scheduled", "published", "archived"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return v.lower()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"blog_post", "case_study", "guide", "whitepaper", "announcement"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid content type. Allowed: {allowed}")
        return v.lower()


class PostResponse(CMSBaseSchema):
    """Post in API responses."""

    id: UUID
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    status: str
    content_type: str
    published_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    og_image_url: Optional[str] = None
    featured_image_url: Optional[str] = None
    featured_image_alt: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    word_count: Optional[int] = None
    view_count: int
    is_featured: bool
    allow_comments: bool
    category: Optional[CategoryResponse] = None
    author: Optional[AuthorResponse] = None
    tags: list[TagResponse] = []
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    """List of posts."""

    posts: list[PostResponse]
    total: int
    page: int
    page_size: int


class PostPublicResponse(CMSBaseSchema):
    """Public post response (no admin fields)."""

    id: UUID
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image_url: Optional[str] = None
    featured_image_url: Optional[str] = None
    featured_image_alt: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    view_count: int
    is_featured: bool
    content_type: str
    category: Optional[CategoryResponse] = None
    author: Optional[AuthorResponse] = None
    tags: list[TagResponse] = []


class PostPublicListResponse(BaseModel):
    """Public list of posts."""

    posts: list[PostPublicResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Page Schemas
# =============================================================================


class PageCreate(BaseModel):
    """Create a new page."""

    title: str = Field(..., min_length=1, max_length=255, description="Page title")
    slug: Optional[str] = Field(None, max_length=255, description="URL-friendly slug")
    content: Optional[str] = Field(None, description="HTML content")
    content_json: Optional[dict[str, Any]] = Field(None, description="TipTap JSON content")
    status: str = Field("draft", description="Page status: draft, published, archived")
    meta_title: Optional[str] = Field(None, max_length=70, description="SEO title")
    meta_description: Optional[str] = Field(None, max_length=160, description="SEO description")
    show_in_navigation: bool = Field(False, description="Show in navigation menu")
    navigation_label: Optional[str] = Field(
        None, max_length=50, description="Navigation menu label"
    )
    navigation_order: int = Field(0, ge=0, description="Navigation display order")
    template: str = Field("default", description="Page template")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"draft", "published", "archived"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return v.lower()


class PageUpdate(BaseModel):
    """Update a page."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    status: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    show_in_navigation: Optional[bool] = None
    navigation_label: Optional[str] = Field(None, max_length=50)
    navigation_order: Optional[int] = Field(None, ge=0)
    template: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"draft", "published", "archived"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return v.lower()


class PageResponse(CMSBaseSchema):
    """Page in API responses."""

    id: UUID
    title: str
    slug: str
    content: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    status: str
    published_at: Optional[datetime] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    show_in_navigation: bool
    navigation_label: Optional[str] = None
    navigation_order: int
    template: str
    created_at: datetime
    updated_at: datetime


class PageListResponse(BaseModel):
    """List of pages."""

    pages: list[PageResponse]
    total: int


# =============================================================================
# Contact Submission Schemas
# =============================================================================


class ContactSubmit(BaseModel):
    """Submit a contact form."""

    name: str = Field(..., min_length=1, max_length=255, description="Contact name")
    email: str = Field(..., min_length=1, max_length=255, description="Contact email")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    subject: Optional[str] = Field(None, max_length=255, description="Message subject")
    message: str = Field(..., min_length=10, max_length=5000, description="Message content")
    source_page: Optional[str] = Field(None, max_length=255, description="Source page URL")


class ContactResponse(CMSBaseSchema):
    """Contact submission in API responses."""

    id: UUID
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str
    source_page: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    is_responded: bool
    responded_at: Optional[datetime] = None
    response_notes: Optional[str] = None
    is_spam: bool
    created_at: datetime


class ContactListResponse(BaseModel):
    """List of contact submissions."""

    contacts: list[ContactResponse]
    total: int
    page: int
    page_size: int


class ContactMarkRead(BaseModel):
    """Mark contact as read."""

    is_read: bool = True


class ContactMarkResponded(BaseModel):
    """Mark contact as responded."""

    is_responded: bool = True
    response_notes: Optional[str] = Field(None, max_length=2000)


class ContactMarkSpam(BaseModel):
    """Mark contact as spam."""

    is_spam: bool = True


# =============================================================================
# API Response Wrappers
# =============================================================================


class CMSAPIResponse(BaseModel):
    """Standard CMS API response wrapper."""

    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[list[dict[str, Any]]] = None
