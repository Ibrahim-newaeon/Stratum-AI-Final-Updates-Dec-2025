# =============================================================================
# Stratum AI - CMS (Content Management System) Database Models
# =============================================================================
"""
Database models for the Stratum CMS module.

Models:
- CMSCategory: Blog categories (Engineering, Product, etc.)
- CMSTag: Content tags (many-to-many with posts)
- CMSAuthor: Content authors (can link to users)
- CMSPost: Blog posts & resources (UUID primary key)
- CMSPage: Generic static pages
- CMSContactSubmission: Contact form submissions

All CMS content is GLOBAL (platform-level, not tenant-scoped).
Managed by superadmins only.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey,
    Index, Boolean, Table
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base, TimestampMixin


# =============================================================================
# Enums
# =============================================================================

class CMSPostStatus(str, enum.Enum):
    """Status of a CMS post."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CMSContentType(str, enum.Enum):
    """Types of CMS content."""
    BLOG_POST = "blog_post"
    CASE_STUDY = "case_study"
    GUIDE = "guide"
    WHITEPAPER = "whitepaper"
    ANNOUNCEMENT = "announcement"


class CMSPageStatus(str, enum.Enum):
    """Status of a CMS page."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# =============================================================================
# Association Table: Posts <-> Tags (Many-to-Many)
# =============================================================================

cms_post_tags = Table(
    "cms_post_tags",
    Base.metadata,
    Column("post_id", UUID(as_uuid=True), ForeignKey("cms_posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("cms_tags.id", ondelete="CASCADE"), primary_key=True),
)


# =============================================================================
# CMS Category Model
# =============================================================================

class CMSCategory(Base, TimestampMixin):
    """
    Blog/content categories.
    Examples: Engineering, Product, Marketing, Company News
    """
    __tablename__ = "cms_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Category identification
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Display settings
    color = Column(String(7), nullable=True)  # Hex color code
    icon = Column(String(50), nullable=True)  # Icon name
    display_order = Column(Integer, nullable=False, default=0)

    # State
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    posts = relationship("CMSPost", back_populates="category", lazy="dynamic")

    __table_args__ = (
        Index("ix_cms_categories_slug", "slug"),
        Index("ix_cms_categories_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CMSCategory {self.name}>"


# =============================================================================
# CMS Tag Model
# =============================================================================

class CMSTag(Base, TimestampMixin):
    """
    Content tags for posts.
    Used for filtering and organization.
    """
    __tablename__ = "cms_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Tag identification
    name = Column(String(50), nullable=False, unique=True)
    slug = Column(String(50), nullable=False, unique=True)

    # Metadata
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code

    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)

    # Relationships
    posts = relationship(
        "CMSPost",
        secondary=cms_post_tags,
        back_populates="tags",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_cms_tags_slug", "slug"),
        Index("ix_cms_tags_usage", "usage_count"),
    )

    def __repr__(self) -> str:
        return f"<CMSTag {self.name}>"


# =============================================================================
# CMS Author Model
# =============================================================================

class CMSAuthor(Base, TimestampMixin):
    """
    Content authors.
    Can be linked to a user account or standalone.
    """
    __tablename__ = "cms_authors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Link to user (optional)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Author details
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    job_title = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)

    # Social links
    twitter_handle = Column(String(50), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    github_handle = Column(String(50), nullable=True)
    website_url = Column(String(255), nullable=True)

    # State
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    posts = relationship("CMSPost", back_populates="author", lazy="dynamic")

    __table_args__ = (
        Index("ix_cms_authors_slug", "slug"),
        Index("ix_cms_authors_user", "user_id"),
        Index("ix_cms_authors_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CMSAuthor {self.name}>"


# =============================================================================
# CMS Post Model
# =============================================================================

class CMSPost(Base, TimestampMixin):
    """
    Blog posts and resources.
    Main content model for the CMS.
    """
    __tablename__ = "cms_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_authors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Content identification
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    excerpt = Column(Text, nullable=True)  # Short description

    # Content body
    content = Column(Text, nullable=True)  # Rendered HTML
    content_json = Column(JSONB, nullable=True)  # TipTap JSON format

    # Status and type
    status = Column(String(20), nullable=False, default=CMSPostStatus.DRAFT.value)
    content_type = Column(String(20), nullable=False, default=CMSContentType.BLOG_POST.value)

    # Publishing
    published_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    # SEO fields
    meta_title = Column(String(70), nullable=True)  # Google recommends < 60 chars
    meta_description = Column(String(160), nullable=True)  # Google recommends < 155 chars
    canonical_url = Column(String(500), nullable=True)
    og_image_url = Column(String(500), nullable=True)  # Open Graph image

    # Featured image
    featured_image_url = Column(String(500), nullable=True)
    featured_image_alt = Column(String(255), nullable=True)

    # Reading metrics
    reading_time_minutes = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)

    # Engagement metrics
    view_count = Column(Integer, nullable=False, default=0)

    # Flags
    is_featured = Column(Boolean, nullable=False, default=False)
    allow_comments = Column(Boolean, nullable=False, default=True)

    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    category = relationship("CMSCategory", back_populates="posts")
    author = relationship("CMSAuthor", back_populates="posts")
    tags = relationship(
        "CMSTag",
        secondary=cms_post_tags,
        back_populates="posts",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_cms_posts_slug", "slug"),
        Index("ix_cms_posts_status", "status"),
        Index("ix_cms_posts_type", "content_type"),
        Index("ix_cms_posts_published", "published_at"),
        Index("ix_cms_posts_featured", "is_featured"),
        Index("ix_cms_posts_category", "category_id"),
        Index("ix_cms_posts_author", "author_id"),
        Index("ix_cms_posts_not_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<CMSPost {self.title} ({self.status})>"

    def soft_delete(self) -> None:
        """Mark the post as deleted."""
        from datetime import datetime, timezone
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True


# =============================================================================
# CMS Page Model
# =============================================================================

class CMSPage(Base, TimestampMixin):
    """
    Generic static pages.
    For About, Terms, Privacy, etc.
    """
    __tablename__ = "cms_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Page identification
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)

    # Content
    content = Column(Text, nullable=True)  # Rendered HTML
    content_json = Column(JSONB, nullable=True)  # TipTap JSON format

    # Status
    status = Column(String(20), nullable=False, default=CMSPageStatus.DRAFT.value)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # SEO fields
    meta_title = Column(String(70), nullable=True)
    meta_description = Column(String(160), nullable=True)

    # Display settings
    show_in_navigation = Column(Boolean, nullable=False, default=False)
    navigation_label = Column(String(50), nullable=True)
    navigation_order = Column(Integer, nullable=False, default=0)

    # Template selection
    template = Column(String(50), nullable=False, default="default")

    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_cms_pages_slug", "slug"),
        Index("ix_cms_pages_status", "status"),
        Index("ix_cms_pages_nav", "show_in_navigation"),
        Index("ix_cms_pages_not_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<CMSPage {self.title} ({self.status})>"

    def soft_delete(self) -> None:
        """Mark the page as deleted."""
        from datetime import datetime, timezone
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True


# =============================================================================
# CMS Contact Submission Model
# =============================================================================

class CMSContactSubmission(Base, TimestampMixin):
    """
    Contact form submissions.
    Stores messages from the public contact form.
    """
    __tablename__ = "cms_contact_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Contact details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Message
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)

    # Context
    source_page = Column(String(255), nullable=True)  # Which page the form was on
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Processing
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    read_by_user_id = Column(Integer, nullable=True)

    # Response tracking
    is_responded = Column(Boolean, nullable=False, default=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_notes = Column(Text, nullable=True)

    # Spam filtering
    is_spam = Column(Boolean, nullable=False, default=False)
    spam_score = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_cms_contacts_email", "email"),
        Index("ix_cms_contacts_read", "is_read"),
        Index("ix_cms_contacts_spam", "is_spam"),
        Index("ix_cms_contacts_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CMSContactSubmission from {self.email}>"
