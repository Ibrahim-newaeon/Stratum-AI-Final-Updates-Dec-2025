# CMS (Content Management System) Specification

## Overview

The Content Management System (CMS) enables managing blog posts, static pages, authors, categories, tags, and contact form submissions for the Stratum AI platform. All CMS content is global (platform-level, not tenant-scoped) and managed by superadmins.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CMS ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    CONTENT TYPES                          │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │  │
│  │  │   Posts      │ │    Pages     │ │   Contact    │     │  │
│  │  │  (Blog)      │ │  (Static)    │ │ Submissions  │     │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘     │  │
│  └─────────┼────────────────┼────────────────┼─────────────┘  │
│            │                │                │                 │
│            └────────────────┴────────────────┘                 │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               WORKFLOW ENGINE (2026)                      │  │
│  │                                                          │  │
│  │  draft → in_review → approved → scheduled → published    │  │
│  │            ↓            ↓                                │  │
│  │    changes_requested  rejected                           │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                   │
│         ┌──────────────────┼──────────────────┐               │
│         ▼                  ▼                  ▼               │
│  ┌───────────┐      ┌───────────┐      ┌───────────┐         │
│  │ Categories│      │   Tags    │      │  Authors  │         │
│  │           │      │  (M2M)    │      │           │         │
│  └───────────┘      └───────────┘      └───────────┘         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   AUDIT & VERSIONING                      │  │
│  │  ┌─────────────┐  ┌─────────────┐                        │  │
│  │  │  Versions   │  │  Workflow   │                        │  │
│  │  │  (content)  │  │    Logs     │                        │  │
│  │  └─────────────┘  └─────────────┘                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### CMSPost

Main content model for blog posts and resources.

```python
class CMSPost:
    id: UUID

    # Foreign keys
    category_id: UUID | None
    author_id: UUID | None

    # Content identification
    title: str                        # Max 255 chars
    slug: str                         # URL-friendly, unique
    excerpt: str | None               # Short description

    # Content body
    content: str | None               # Rendered HTML
    content_json: dict | None         # TipTap JSON format

    # Status and type
    status: CMSPostStatus             # draft, in_review, published, etc.
    content_type: CMSContentType      # blog_post, case_study, guide, etc.

    # Publishing
    published_at: datetime | None
    scheduled_at: datetime | None

    # SEO fields
    meta_title: str | None            # Max 70 chars
    meta_description: str | None      # Max 160 chars
    canonical_url: str | None
    og_image_url: str | None

    # Featured image
    featured_image_url: str | None
    featured_image_alt: str | None

    # Reading metrics
    reading_time_minutes: int | None
    word_count: int | None
    view_count: int = 0

    # Flags
    is_featured: bool = False
    allow_comments: bool = True
    is_deleted: bool = False

    # Workflow tracking (2026)
    submitted_at: datetime | None
    submitted_by_id: int | None
    reviewed_at: datetime | None
    reviewed_by_id: int | None
    review_notes: str | None
    approved_at: datetime | None
    approved_by_id: int | None
    rejected_at: datetime | None
    rejected_by_id: int | None
    rejection_reason: str | None

    # Versioning
    version: int = 1
    current_version_id: UUID | None

    # Assigned reviewer
    assigned_reviewer_id: int | None
    review_due_date: datetime | None

    # Edit lock
    locked_by_id: int | None
    locked_at: datetime | None
```

### CMSPostStatus Enum

```python
class CMSPostStatus(str, Enum):
    DRAFT = "draft"                    # Initial state, being written
    IN_REVIEW = "in_review"            # Submitted for review
    CHANGES_REQUESTED = "changes_requested"  # Reviewer requested changes
    APPROVED = "approved"              # Approved, ready to publish/schedule
    SCHEDULED = "scheduled"            # Scheduled for future publish
    PUBLISHED = "published"            # Live and visible
    UNPUBLISHED = "unpublished"        # Taken offline temporarily
    ARCHIVED = "archived"              # Permanently archived
    REJECTED = "rejected"              # Rejected by reviewer
```

### CMSContentType Enum

```python
class CMSContentType(str, Enum):
    BLOG_POST = "blog_post"
    CASE_STUDY = "case_study"
    GUIDE = "guide"
    WHITEPAPER = "whitepaper"
    ANNOUNCEMENT = "announcement"
    NEWSLETTER = "newsletter"
    PRESS_RELEASE = "press_release"
```

### CMSCategory

```python
class CMSCategory:
    id: UUID
    name: str                   # Max 100 chars, unique
    slug: str                   # Max 100 chars, unique
    description: str | None
    color: str | None           # Hex color code (#RRGGBB)
    icon: str | None            # Icon name
    display_order: int = 0
    is_active: bool = True
```

### CMSTag

```python
class CMSTag:
    id: UUID
    name: str                   # Max 50 chars, unique
    slug: str                   # Max 50 chars, unique
    description: str | None
    color: str | None           # Hex color code
    usage_count: int = 0        # Auto-tracked
```

### CMSAuthor

```python
class CMSAuthor:
    id: UUID
    user_id: int | None         # Link to user account (optional)
    name: str                   # Max 255 chars
    slug: str                   # Max 100 chars, unique
    email: str | None
    bio: str | None
    avatar_url: str | None
    job_title: str | None
    company: str | None

    # Social links
    twitter_handle: str | None
    linkedin_url: str | None
    github_handle: str | None
    website_url: str | None

    is_active: bool = True
```

### CMSPage

Static pages (About, Terms, Privacy, etc.).

```python
class CMSPage:
    id: UUID
    title: str
    slug: str                   # Unique
    content: str | None         # Rendered HTML
    content_json: dict | None   # TipTap JSON format
    status: CMSPageStatus
    published_at: datetime | None

    # SEO
    meta_title: str | None
    meta_description: str | None

    # Navigation
    show_in_navigation: bool = False
    navigation_label: str | None
    navigation_order: int = 0
    template: str = "default"

    is_deleted: bool = False
```

### CMSContactSubmission

```python
class CMSContactSubmission:
    id: UUID
    name: str
    email: str
    company: str | None
    phone: str | None
    subject: str | None
    message: str
    source_page: str | None
    ip_address: str | None
    user_agent: str | None

    # Processing
    is_read: bool = False
    read_at: datetime | None
    read_by_user_id: int | None

    # Response tracking
    is_responded: bool = False
    responded_at: datetime | None
    response_notes: str | None

    # Spam filtering
    is_spam: bool = False
    spam_score: int | None
```

---

## Content Versioning (2026)

### CMSPostVersion

Stores complete snapshots of post content for audit trail and rollback.

```python
class CMSPostVersion:
    id: UUID
    post_id: UUID
    version: int                    # Auto-incremented per post

    # Content snapshot
    title: str
    slug: str
    excerpt: str | None
    content: str | None
    content_json: dict | None

    # Metadata snapshot
    meta_title: str | None
    meta_description: str | None
    featured_image_url: str | None

    # Who created this version
    created_by_id: int | None

    # Change summary
    change_summary: str | None      # Brief description
    change_type: str | None         # content_update, seo_update, media_update

    # Metrics at this version
    word_count: int | None
    reading_time_minutes: int | None
```

---

## Workflow Audit Log

### CMSWorkflowLog

Records all status changes and workflow actions.

```python
class CMSWorkflowLog:
    id: UUID
    post_id: UUID

    # Action details
    action: CMSWorkflowAction       # created, updated, approved, etc.
    from_status: str | None         # Previous status
    to_status: str | None           # New status

    # Actor
    performed_by_id: int | None
    performed_by_role: str | None   # CMSRole at time of action

    # Context
    comment: str | None             # Review notes, rejection reason
    extra_data: dict | None         # Additional structured data
    version_number: int | None      # Which version was affected

    # Security audit
    ip_address: str | None
    user_agent: str | None
```

### CMSWorkflowAction Enum

```python
class CMSWorkflowAction(str, Enum):
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
```

---

## Role-Based Access Control (RBAC)

### CMSRole Enum

```python
class CMSRole(str, Enum):
    SUPER_ADMIN = "super_admin"           # Full system access
    ADMIN = "admin"                        # Tenant-wide CMS access
    EDITOR_IN_CHIEF = "editor_in_chief"   # Approve/reject, publish, manage authors
    EDITOR = "editor"                      # Edit all content, schedule, review
    AUTHOR = "author"                      # Create/edit own content, submit for review
    CONTRIBUTOR = "contributor"            # Create drafts only, no publish
    REVIEWER = "reviewer"                  # Comment, approve/reject, no edit
    VIEWER = "viewer"                      # Read-only access
```

### Permission Matrix

| Permission | Super Admin | Admin | Editor-in-Chief | Editor | Author | Contributor | Reviewer | Viewer |
|------------|-------------|-------|-----------------|--------|--------|-------------|----------|--------|
| create_post | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| edit_any_post | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| edit_own_post | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| delete_any_post | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| publish_post | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| schedule_post | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| submit_for_review | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| approve_post | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| reject_post | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| request_changes | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| view_all_posts | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| manage_categories | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| manage_tags | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| manage_authors | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| manage_pages | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| view_analytics | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| export_content | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| bulk_operations | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| access_settings | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Workflow State Machine

```
                                    ┌─────────────┐
                                    │   DRAFT     │
                                    └──────┬──────┘
                                           │ submit_for_review
                                           ▼
                                    ┌─────────────┐
                              ┌─────│  IN_REVIEW  │─────┐
                              │     └──────┬──────┘     │
                    approve   │            │            │ reject
                              │            │            │
                              ▼            ▼            ▼
                       ┌──────────┐ request_changes ┌──────────┐
                       │ APPROVED │◄──────────────►│ REJECTED │
                       └────┬─────┘      │         └──────────┘
                            │            │               │
              publish       │            ▼               │ resubmit
                            │   ┌─────────────────┐      │
                            │   │ CHANGES_REQUESTED│◄────┘
                            │   └─────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │ schedule         │ publish          │
         ▼                  ▼                  ▼
  ┌───────────┐      ┌─────────────┐    ┌─────────────┐
  │ SCHEDULED │──────│  PUBLISHED  │───►│ UNPUBLISHED │
  └───────────┘      └──────┬──────┘    └─────────────┘
         auto-publish       │                  │
                           │ archive          │
                           ▼                  ▼
                    ┌─────────────┐
                    │  ARCHIVED   │
                    └─────────────┘
```

---

## SEO Features

### Meta Fields

| Field | Max Length | Description |
|-------|------------|-------------|
| `meta_title` | 70 chars | Title tag for search engines |
| `meta_description` | 160 chars | Description for search snippets |
| `canonical_url` | 500 chars | Canonical URL for duplicate content |
| `og_image_url` | 500 chars | Open Graph image for social sharing |

### Auto-Generated Fields

- **Reading Time**: Calculated from word count (200 WPM average)
- **Word Count**: Auto-counted from content
- **Slug**: Auto-generated from title if not provided

```python
def calculate_reading_time(content: str) -> int:
    words = len(re.findall(r"\w+", content))
    return max(1, round(words / 200))

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text
```

---

## Content Types for Landing Page

### Feature Layers
- Category: `landing-features`
- Structure: Posts with layer metadata

### FAQ Items
- Categories: `landing-faq`, `faq-pricing`, `faq-features`, etc.
- Structure: Title = Question, Content = Answer

### Pricing Tiers
- Category: `landing-pricing`
- Metadata: price, period, features[], cta, highlighted

### Trust Badges
- Category: `landing-trust-badges`
- Metadata: icon, displayOrder

---

## Database Schema

```sql
-- Categories
CREATE TABLE cms_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7),
    icon VARCHAR(50),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tags
CREATE TABLE cms_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7),
    usage_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Authors
CREATE TABLE cms_authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255),
    bio TEXT,
    avatar_url VARCHAR(500),
    job_title VARCHAR(100),
    company VARCHAR(100),
    twitter_handle VARCHAR(50),
    linkedin_url VARCHAR(255),
    github_handle VARCHAR(50),
    website_url VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Posts
CREATE TABLE cms_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES cms_categories(id) ON DELETE SET NULL,
    author_id UUID REFERENCES cms_authors(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    excerpt TEXT,
    content TEXT,
    content_json JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    content_type VARCHAR(20) NOT NULL DEFAULT 'blog_post',
    published_at TIMESTAMPTZ,
    scheduled_at TIMESTAMPTZ,
    meta_title VARCHAR(70),
    meta_description VARCHAR(160),
    canonical_url VARCHAR(500),
    og_image_url VARCHAR(500),
    featured_image_url VARCHAR(500),
    featured_image_alt VARCHAR(255),
    reading_time_minutes INTEGER,
    word_count INTEGER,
    view_count INTEGER NOT NULL DEFAULT 0,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    allow_comments BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Post-Tag Association
CREATE TABLE cms_post_tags (
    post_id UUID REFERENCES cms_posts(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES cms_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

-- Versions
CREATE TABLE cms_post_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES cms_posts(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    excerpt TEXT,
    content TEXT,
    content_json JSONB,
    meta_title VARCHAR(70),
    meta_description VARCHAR(160),
    featured_image_url VARCHAR(500),
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    change_summary VARCHAR(500),
    change_type VARCHAR(50),
    word_count INTEGER,
    reading_time_minutes INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow Logs
CREATE TABLE cms_workflow_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES cms_posts(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    from_status VARCHAR(20),
    to_status VARCHAR(20),
    performed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    performed_by_role VARCHAR(50),
    comment TEXT,
    extra_data JSONB,
    version_number INTEGER,
    ip_address VARCHAR(45),
    user_agent VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Configuration

### Environment Variables

```bash
# CMS Settings
CMS_DEFAULT_PAGE_SIZE=10
CMS_MAX_PAGE_SIZE=50
CMS_SLUG_MAX_LENGTH=255
CMS_ENABLE_COMMENTS=true
CMS_AUTO_PUBLISH_SCHEDULED=true
```

### Feature Flags

| Flag | Description |
|------|-------------|
| `cms_enabled` | Enable CMS module |
| `cms_workflow_enabled` | Enable 2026 workflow features |
| `cms_versioning_enabled` | Enable content versioning |
| `cms_contact_form_enabled` | Enable contact form |
| `cms_comments_enabled` | Enable post comments |

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
