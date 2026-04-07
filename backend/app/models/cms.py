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

import enum
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base, TimestampMixin

# =============================================================================
# Enums
# =============================================================================


class CMSRole(str, enum.Enum):
    """CMS-specific roles for content management (2026 Standard)."""

    SUPER_ADMIN = "super_admin"  # Full system access
    ADMIN = "admin"  # Tenant-wide CMS access
    EDITOR_IN_CHIEF = "editor_in_chief"  # Approve/reject, publish, manage authors
    EDITOR = "editor"  # Edit all content, schedule, review
    AUTHOR = "author"  # Create/edit own content, submit for review
    CONTRIBUTOR = "contributor"  # Create drafts only, no publish
    REVIEWER = "reviewer"  # Comment, approve/reject, no edit
    VIEWER = "viewer"  # Read-only access


class CMSPostStatus(str, enum.Enum):
    """Status of a CMS post (2026 Workflow Standard)."""

    DRAFT = "draft"  # Initial state, being written
    IN_REVIEW = "in_review"  # Submitted for review
    CHANGES_REQUESTED = "changes_requested"  # Reviewer requested changes
    APPROVED = "approved"  # Approved, ready to publish/schedule
    SCHEDULED = "scheduled"  # Scheduled for future publish
    PUBLISHED = "published"  # Live and visible
    UNPUBLISHED = "unpublished"  # Taken offline temporarily
    ARCHIVED = "archived"  # Permanently archived
    REJECTED = "rejected"  # Rejected by reviewer


class CMSContentType(str, enum.Enum):
    """Types of CMS content."""

    BLOG_POST = "blog_post"
    CASE_STUDY = "case_study"
    GUIDE = "guide"
    WHITEPAPER = "whitepaper"
    ANNOUNCEMENT = "announcement"
    NEWSLETTER = "newsletter"
    PRESS_RELEASE = "press_release"


class CMSPageStatus(str, enum.Enum):
    """Status of a CMS page."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CMSWorkflowAction(str, enum.Enum):
    """Workflow actions for audit trail."""

    CREATED = "created"
    UPDATED = "updated"
    SUBMITTED_FOR_REVIEW = "submitted_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    ARCHIVED = "archived"
    RESTORED = "restored"
    DELETED = "deleted"


# =============================================================================
# Association Table: Posts <-> Tags (Many-to-Many)
# =============================================================================

cms_post_tags = Table(
    "cms_post_tags",
    Base.metadata,
    Column(
        "post_id",
        UUID(as_uuid=True),
        ForeignKey("cms_posts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("cms_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
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

    # ==========================================================================
    # 2026 Workflow Fields
    # ==========================================================================

    # Workflow tracking
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Review tracking
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Approval tracking
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Rejection tracking
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    current_version_id = Column(UUID(as_uuid=True), nullable=True)  # Points to latest version

    # Assigned reviewer (for workflow)
    assigned_reviewer_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_due_date = Column(DateTime(timezone=True), nullable=True)

    # Lock for editing (prevent conflicts)
    locked_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    category = relationship("CMSCategory", back_populates="posts")
    author = relationship("CMSAuthor", back_populates="posts")
    tags = relationship(
        "CMSTag",
        secondary=cms_post_tags,
        back_populates="posts",
        lazy="selectin",
    )
    versions = relationship(
        "CMSPostVersion",
        back_populates="post",
        lazy="dynamic",
        order_by="desc(CMSPostVersion.version)",
    )
    workflow_history = relationship(
        "CMSWorkflowLog",
        back_populates="post",
        lazy="dynamic",
        order_by="desc(CMSWorkflowLog.created_at)",
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
        Index("ix_cms_posts_scheduled", "scheduled_at"),
        Index("ix_cms_posts_reviewer", "assigned_reviewer_id"),
    )

    def __repr__(self) -> str:
        return f"<CMSPost {self.title} ({self.status}) v{self.version}>"

    def soft_delete(self) -> None:
        """Mark the post as deleted."""
        from datetime import datetime

        self.deleted_at = datetime.now(UTC)
        self.is_deleted = True

    def submit_for_review(self, user_id: int) -> None:
        """Submit post for review."""
        from datetime import datetime

        self.status = CMSPostStatus.IN_REVIEW.value
        self.submitted_at = datetime.now(UTC)
        self.submitted_by_id = user_id

    def approve(self, user_id: int, notes: Optional[str] = None) -> None:
        """Approve the post."""
        from datetime import datetime

        self.status = CMSPostStatus.APPROVED.value
        self.approved_at = datetime.now(UTC)
        self.approved_by_id = user_id
        self.reviewed_at = datetime.now(UTC)
        self.reviewed_by_id = user_id
        if notes:
            self.review_notes = notes

    def reject(self, user_id: int, reason: str) -> None:
        """Reject the post."""
        from datetime import datetime

        self.status = CMSPostStatus.REJECTED.value
        self.rejected_at = datetime.now(UTC)
        self.rejected_by_id = user_id
        self.rejection_reason = reason
        self.reviewed_at = datetime.now(UTC)
        self.reviewed_by_id = user_id

    def request_changes(self, user_id: int, notes: str) -> None:
        """Request changes on the post."""
        from datetime import datetime

        self.status = CMSPostStatus.CHANGES_REQUESTED.value
        self.reviewed_at = datetime.now(UTC)
        self.reviewed_by_id = user_id
        self.review_notes = notes

    def publish(self) -> None:
        """Publish the post."""
        from datetime import datetime

        self.status = CMSPostStatus.PUBLISHED.value
        self.published_at = datetime.now(UTC)

    def schedule(self, publish_at: datetime) -> None:
        """Schedule the post for future publishing."""
        self.status = CMSPostStatus.SCHEDULED.value
        self.scheduled_at = publish_at


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
        from datetime import datetime

        self.deleted_at = datetime.now(UTC)
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


# =============================================================================
# CMS Post Version Model (2026 Content Versioning)
# =============================================================================


class CMSPostVersion(Base, TimestampMixin):
    """
    Content versioning for posts.
    Stores complete snapshots of post content for audit trail and rollback.

    2026 Standard: Every content change creates a new version.
    """

    __tablename__ = "cms_post_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Link to parent post
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version number (auto-incremented per post)
    version = Column(Integer, nullable=False)

    # Content snapshot
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    content_json = Column(JSONB, nullable=True)

    # Metadata snapshot
    meta_title = Column(String(70), nullable=True)
    meta_description = Column(String(160), nullable=True)
    featured_image_url = Column(String(500), nullable=True)

    # Who created this version
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Change summary
    change_summary = Column(String(500), nullable=True)  # Brief description of changes
    change_type = Column(
        String(50), nullable=True
    )  # content_update, seo_update, media_update, etc.

    # Word/reading metrics at this version
    word_count = Column(Integer, nullable=True)
    reading_time_minutes = Column(Integer, nullable=True)

    # Relationships
    post = relationship("CMSPost", back_populates="versions")

    __table_args__ = (
        Index("ix_cms_post_versions_post", "post_id"),
        Index("ix_cms_post_versions_version", "post_id", "version"),
        Index("ix_cms_post_versions_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CMSPostVersion post={self.post_id} v{self.version}>"


# =============================================================================
# CMS Workflow Log Model (2026 Audit Trail)
# =============================================================================


class CMSWorkflowLog(Base, TimestampMixin):
    """
    Workflow audit log for posts.
    Records all status changes and workflow actions.

    2026 Standard: Complete audit trail for compliance and transparency.
    """

    __tablename__ = "cms_workflow_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Link to post
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Action details
    action = Column(String(50), nullable=False)  # CMSWorkflowAction value

    # Status transition
    from_status = Column(String(20), nullable=True)  # Previous status
    to_status = Column(String(20), nullable=True)  # New status

    # Actor
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    performed_by_role = Column(String(50), nullable=True)  # CMSRole value at time of action

    # Context
    comment = Column(Text, nullable=True)  # Review notes, rejection reason, etc.
    extra_data = Column(
        JSONB, nullable=True
    )  # Additional structured data (renamed from metadata - reserved)

    # Version reference (which version was affected)
    version_number = Column(Integer, nullable=True)

    # IP and user agent for security audit
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Relationships
    post = relationship("CMSPost", back_populates="workflow_history")

    __table_args__ = (
        Index("ix_cms_workflow_logs_post", "post_id"),
        Index("ix_cms_workflow_logs_action", "action"),
        Index("ix_cms_workflow_logs_user", "performed_by_id"),
        Index("ix_cms_workflow_logs_created", "created_at"),
        Index("ix_cms_workflow_logs_status", "to_status"),
    )

    def __repr__(self) -> str:
        return f"<CMSWorkflowLog {self.action} on post={self.post_id}>"


# =============================================================================
# CMS Permission Matrix (2026 RBAC)
# =============================================================================

# Define what each role can do
CMS_PERMISSIONS = {
    CMSRole.SUPER_ADMIN: {
        "create_post": True,
        "edit_any_post": True,
        "delete_any_post": True,
        "publish_post": True,
        "schedule_post": True,
        "submit_for_review": True,
        "approve_post": True,
        "reject_post": True,
        "request_changes": True,
        "view_all_posts": True,
        "manage_categories": True,
        "manage_tags": True,
        "manage_authors": True,
        "manage_pages": True,
        "manage_users": True,
        "view_analytics": True,
        "export_content": True,
        "bulk_operations": True,
        "access_settings": True,
    },
    CMSRole.ADMIN: {
        "create_post": True,
        "edit_any_post": True,
        "delete_any_post": True,
        "publish_post": True,
        "schedule_post": True,
        "submit_for_review": True,
        "approve_post": True,
        "reject_post": True,
        "request_changes": True,
        "view_all_posts": True,
        "manage_categories": True,
        "manage_tags": True,
        "manage_authors": True,
        "manage_pages": True,
        "manage_users": False,  # Can't manage users
        "view_analytics": True,
        "export_content": True,
        "bulk_operations": True,
        "access_settings": False,
    },
    CMSRole.EDITOR_IN_CHIEF: {
        "create_post": True,
        "edit_any_post": True,
        "delete_any_post": False,  # Soft delete only
        "publish_post": True,
        "schedule_post": True,
        "submit_for_review": True,
        "approve_post": True,
        "reject_post": True,
        "request_changes": True,
        "view_all_posts": True,
        "manage_categories": True,
        "manage_tags": True,
        "manage_authors": True,
        "manage_pages": False,
        "manage_users": False,
        "view_analytics": True,
        "export_content": True,
        "bulk_operations": True,
        "access_settings": False,
    },
    CMSRole.EDITOR: {
        "create_post": True,
        "edit_any_post": True,
        "delete_any_post": False,
        "publish_post": False,  # Can schedule but not publish directly
        "schedule_post": True,
        "submit_for_review": True,
        "approve_post": False,
        "reject_post": False,
        "request_changes": True,
        "view_all_posts": True,
        "manage_categories": False,
        "manage_tags": True,
        "manage_authors": False,
        "manage_pages": False,
        "manage_users": False,
        "view_analytics": True,
        "export_content": False,
        "bulk_operations": False,
        "access_settings": False,
    },
    CMSRole.AUTHOR: {
        "create_post": True,
        "edit_own_post": True,
        "edit_any_post": False,
        "delete_any_post": False,
        "publish_post": False,
        "schedule_post": False,
        "submit_for_review": True,
        "approve_post": False,
        "reject_post": False,
        "request_changes": False,
        "view_all_posts": False,
        "view_own_posts": True,
        "manage_categories": False,
        "manage_tags": False,
        "manage_authors": False,
        "manage_pages": False,
        "manage_users": False,
        "view_analytics": False,
        "export_content": False,
        "bulk_operations": False,
        "access_settings": False,
    },
    CMSRole.CONTRIBUTOR: {
        "create_post": True,  # Can create drafts only
        "edit_own_post": True,
        "edit_any_post": False,
        "delete_any_post": False,
        "publish_post": False,
        "schedule_post": False,
        "submit_for_review": False,  # Cannot submit, needs author+ role
        "approve_post": False,
        "reject_post": False,
        "request_changes": False,
        "view_all_posts": False,
        "view_own_posts": True,
        "manage_categories": False,
        "manage_tags": False,
        "manage_authors": False,
        "manage_pages": False,
        "manage_users": False,
        "view_analytics": False,
        "export_content": False,
        "bulk_operations": False,
        "access_settings": False,
    },
    CMSRole.REVIEWER: {
        "create_post": False,
        "edit_own_post": False,
        "edit_any_post": False,
        "delete_any_post": False,
        "publish_post": False,
        "schedule_post": False,
        "submit_for_review": False,
        "approve_post": True,  # Can approve/reject
        "reject_post": True,
        "request_changes": True,
        "view_all_posts": True,  # Needs to view all to review
        "view_own_posts": True,
        "manage_categories": False,
        "manage_tags": False,
        "manage_authors": False,
        "manage_pages": False,
        "manage_users": False,
        "view_analytics": False,
        "export_content": False,
        "bulk_operations": False,
        "access_settings": False,
    },
    CMSRole.VIEWER: {
        "create_post": False,
        "edit_own_post": False,
        "edit_any_post": False,
        "delete_any_post": False,
        "publish_post": False,
        "schedule_post": False,
        "submit_for_review": False,
        "approve_post": False,
        "reject_post": False,
        "request_changes": False,
        "view_all_posts": True,  # Can view all published
        "view_own_posts": False,
        "manage_categories": False,
        "manage_tags": False,
        "manage_authors": False,
        "manage_pages": False,
        "manage_users": False,
        "view_analytics": False,
        "export_content": False,
        "bulk_operations": False,
        "access_settings": False,
    },
}


def has_permission(role: CMSRole, permission: str) -> bool:
    """Check if a CMS role has a specific permission."""
    role_permissions = CMS_PERMISSIONS.get(role, {})
    return role_permissions.get(permission, False)
