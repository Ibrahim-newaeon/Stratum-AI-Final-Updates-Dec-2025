# CMS API Contracts

## Overview

API endpoints for the Content Management System. Public endpoints serve published content; admin endpoints require superadmin authentication.

**Base URL**: `/api/v1/cms`

---

## Authentication

- **Public endpoints**: No authentication required
- **Admin endpoints**: Bearer token with superadmin role

---

## Public Endpoints

### GET /posts

List published posts.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (max: 50, default: 10) |
| `category_slug` | string | Filter by category slug |
| `tag_slug` | string | Filter by tag slug |
| `content_type` | string | Filter by content type |
| `search` | string | Search in title and excerpt |
| `featured_only` | boolean | Only featured posts |

#### Response

```json
{
  "success": true,
  "data": {
    "posts": [
      {
        "id": "uuid-...",
        "title": "Introduction to Trust-Gated Automation",
        "slug": "introduction-to-trust-gated-automation",
        "excerpt": "Learn how trust gates ensure safe automation...",
        "content": "<p>Full HTML content...</p>",
        "published_at": "2024-01-15T10:00:00Z",
        "meta_title": "Trust-Gated Automation | Stratum AI",
        "meta_description": "Learn how trust gates ensure...",
        "og_image_url": "https://cdn.stratum.ai/og/post-123.jpg",
        "featured_image_url": "https://cdn.stratum.ai/images/post-123.jpg",
        "featured_image_alt": "Trust gate diagram",
        "reading_time_minutes": 8,
        "view_count": 1250,
        "is_featured": true,
        "content_type": "blog_post",
        "category": {
          "id": "uuid-...",
          "name": "Engineering",
          "slug": "engineering",
          "color": "#3B82F6"
        },
        "author": {
          "id": "uuid-...",
          "name": "John Doe",
          "slug": "john-doe",
          "avatar_url": "https://cdn.stratum.ai/avatars/john.jpg",
          "bio": "Senior Engineer at Stratum"
        },
        "tags": [
          {
            "id": "uuid-...",
            "name": "Automation",
            "slug": "automation"
          }
        ]
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 10
  }
}
```

### GET /posts/{slug}

Get a single published post by slug. Increments view count.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "title": "Introduction to Trust-Gated Automation",
    "slug": "introduction-to-trust-gated-automation",
    "excerpt": "Learn how trust gates ensure safe automation...",
    "content": "<p>Full HTML content...</p>",
    "published_at": "2024-01-15T10:00:00Z",
    "view_count": 1251,
    "category": { ... },
    "author": { ... },
    "tags": [ ... ]
  }
}
```

### GET /categories

List categories.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `active_only` | boolean | Only active categories (default: true) |

#### Response

```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": "uuid-...",
        "name": "Engineering",
        "slug": "engineering",
        "description": "Technical articles and tutorials",
        "color": "#3B82F6",
        "icon": "code",
        "display_order": 0,
        "is_active": true
      }
    ],
    "total": 5
  }
}
```

### GET /tags

List all tags.

#### Response

```json
{
  "success": true,
  "data": {
    "tags": [
      {
        "id": "uuid-...",
        "name": "Automation",
        "slug": "automation",
        "description": "Articles about automation",
        "color": "#10B981",
        "usage_count": 12
      }
    ],
    "total": 25
  }
}
```

### POST /contact

Submit contact form.

#### Request

```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "company": "Acme Corp",
  "phone": "+1-555-0123",
  "subject": "Product Inquiry",
  "message": "I'm interested in learning more about...",
  "source_page": "/pricing"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "submitted": true
  }
}
```

---

## Admin Endpoints

### Posts

#### GET /admin/posts

List all posts (any status).

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `page_size` | integer | Items per page |
| `status_filter` | string | Filter by status |
| `content_type` | string | Filter by content type |
| `search` | string | Search in title |

##### Response

```json
{
  "success": true,
  "data": {
    "posts": [
      {
        "id": "uuid-...",
        "title": "Draft Post",
        "slug": "draft-post",
        "status": "draft",
        "content_type": "blog_post",
        "version": 3,
        "created_at": "2024-01-10T10:00:00Z",
        "updated_at": "2024-01-14T15:30:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

#### GET /admin/posts/{id}

Get post by ID with full details.

#### POST /admin/posts

Create a new post.

##### Request

```json
{
  "title": "New Blog Post",
  "slug": "new-blog-post",
  "excerpt": "Short description...",
  "content": "<p>HTML content</p>",
  "content_json": { "type": "doc", "content": [...] },
  "status": "draft",
  "content_type": "blog_post",
  "category_id": "uuid-...",
  "author_id": "uuid-...",
  "tag_ids": ["uuid-1", "uuid-2"],
  "meta_title": "New Post | Stratum",
  "meta_description": "Description for search engines",
  "featured_image_url": "https://...",
  "is_featured": false,
  "allow_comments": true
}
```

##### Response

```json
{
  "success": true,
  "data": {
    "id": "uuid-...",
    "title": "New Blog Post",
    "slug": "new-blog-post",
    "status": "draft",
    "version": 1
  }
}
```

#### PATCH /admin/posts/{id}

Update a post. Creates new version automatically.

##### Request

```json
{
  "title": "Updated Title",
  "content": "<p>Updated content</p>"
}
```

#### DELETE /admin/posts/{id}

Soft delete a post.

---

### Workflow Endpoints (2026)

#### POST /admin/posts/{id}/submit-for-review

Submit post for editorial review.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `reviewer_id` | integer | Assign specific reviewer |

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "status": "in_review",
    "submitted_at": "2024-01-14T16:45:00Z",
    "assigned_reviewer_id": 123
  }
}
```

#### POST /admin/posts/{id}/approve

Approve post for publishing.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `notes` | string | Approval notes |

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "status": "approved",
    "approved_at": "2024-01-15T11:00:00Z",
    "review_notes": "Good to go!"
  }
}
```

#### POST /admin/posts/{id}/reject

Reject post.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `reason` | string | Rejection reason (required) |

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "status": "rejected",
    "rejected_at": "2024-01-15T11:00:00Z",
    "rejection_reason": "Content doesn't meet guidelines"
  }
}
```

#### POST /admin/posts/{id}/request-changes

Request changes from author.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `notes` | string | Change notes (required) |

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "status": "changes_requested",
    "review_notes": "Please update the introduction..."
  }
}
```

#### POST /admin/posts/{id}/schedule

Schedule post for future publishing.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `scheduled_at` | string | ISO 8601 datetime (required) |

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "status": "scheduled",
    "scheduled_at": "2024-01-20T09:00:00Z"
  }
}
```

#### POST /admin/posts/{id}/publish

Publish post immediately.

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "status": "published",
    "published_at": "2024-01-15T14:30:00Z"
  }
}
```

#### POST /admin/posts/{id}/unpublish

Take post offline temporarily.

#### POST /admin/posts/{id}/archive

Archive post permanently.

---

### Version Endpoints

#### GET /admin/posts/{id}/versions

Get version history for a post.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "current_version": 5,
    "versions": [
      {
        "id": "uuid-...",
        "version": 5,
        "title": "Latest Title",
        "slug": "latest-title",
        "change_summary": "SEO improvements",
        "change_type": "seo_update",
        "word_count": 1250,
        "reading_time_minutes": 6,
        "created_by_id": 123,
        "created_at": "2024-01-14T15:30:00Z"
      },
      {
        "id": "uuid-...",
        "version": 4,
        "title": "Previous Title",
        "change_summary": "Content update",
        "change_type": "content_update",
        "created_at": "2024-01-13T10:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

#### POST /admin/posts/{id}/restore-version/{version}

Restore post to a previous version.

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "restored_from_version": 3,
    "new_version": 6
  }
}
```

---

### Workflow History

#### GET /admin/posts/{id}/workflow-history

Get workflow audit log for a post.

##### Response

```json
{
  "success": true,
  "data": {
    "post_id": "uuid-...",
    "history": [
      {
        "id": "uuid-...",
        "action": "published",
        "from_status": "approved",
        "to_status": "published",
        "performed_by_id": 456,
        "comment": null,
        "version_number": 5,
        "created_at": "2024-01-15T14:30:00Z"
      },
      {
        "id": "uuid-...",
        "action": "approved",
        "from_status": "in_review",
        "to_status": "approved",
        "performed_by_id": 789,
        "comment": "Good to go!",
        "version_number": 5,
        "created_at": "2024-01-15T11:00:00Z"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

---

### Categories

#### GET /admin/categories

List all categories.

#### POST /admin/categories

Create category.

```json
{
  "name": "Engineering",
  "slug": "engineering",
  "description": "Technical articles",
  "color": "#3B82F6",
  "icon": "code",
  "display_order": 0,
  "is_active": true
}
```

#### PATCH /admin/categories/{id}

Update category.

#### DELETE /admin/categories/{id}

Delete category. Posts moved to uncategorized.

---

### Tags

#### GET /admin/tags

List all tags.

#### POST /admin/tags

Create tag.

```json
{
  "name": "Machine Learning",
  "slug": "machine-learning",
  "description": "ML-related content",
  "color": "#8B5CF6"
}
```

#### PATCH /admin/tags/{id}

Update tag.

#### DELETE /admin/tags/{id}

Delete tag. Removed from all posts.

---

### Authors

#### GET /admin/authors

List all authors.

#### POST /admin/authors

Create author.

```json
{
  "name": "John Doe",
  "slug": "john-doe",
  "email": "john@stratum.ai",
  "bio": "Senior Engineer at Stratum...",
  "avatar_url": "https://...",
  "job_title": "Senior Engineer",
  "company": "Stratum AI",
  "twitter_handle": "johndoe",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "github_handle": "johndoe",
  "website_url": "https://johndoe.com",
  "user_id": 123,
  "is_active": true
}
```

#### PATCH /admin/authors/{id}

Update author.

#### DELETE /admin/authors/{id}

Delete author. Posts keep author reference but show as deleted.

---

### Pages

#### GET /admin/pages

List all pages.

#### POST /admin/pages

Create page.

```json
{
  "title": "Terms of Service",
  "slug": "terms",
  "content": "<h1>Terms</h1>...",
  "content_json": { ... },
  "status": "draft",
  "meta_title": "Terms of Service | Stratum",
  "meta_description": "Read our terms...",
  "show_in_navigation": true,
  "navigation_label": "Terms",
  "navigation_order": 1,
  "template": "default"
}
```

#### PATCH /admin/pages/{id}

Update page.

#### DELETE /admin/pages/{id}

Soft delete page.

---

### Contacts

#### GET /admin/contacts

List contact submissions.

##### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `page_size` | integer | Items per page |
| `unread_only` | boolean | Filter unread only |
| `exclude_spam` | boolean | Exclude spam |

##### Response

```json
{
  "success": true,
  "data": {
    "contacts": [
      {
        "id": "uuid-...",
        "name": "Jane Smith",
        "email": "jane@example.com",
        "company": "Acme Corp",
        "subject": "Product Inquiry",
        "message": "I'm interested in...",
        "source_page": "/pricing",
        "is_read": false,
        "is_responded": false,
        "is_spam": false,
        "created_at": "2024-01-15T16:00:00Z"
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 10
  }
}
```

#### PATCH /admin/contacts/{id}/read

Mark contact as read/unread.

```json
{
  "is_read": true
}
```

#### PATCH /admin/contacts/{id}/responded

Mark contact as responded.

```json
{
  "is_responded": true,
  "response_notes": "Sent follow-up email"
}
```

#### PATCH /admin/contacts/{id}/spam

Mark contact as spam.

```json
{
  "is_spam": true
}
```

---

## Schemas

### PostCreate

```typescript
interface PostCreate {
  title: string                    // Required, max 255
  slug?: string                    // Auto-generated if not provided
  excerpt?: string
  content?: string                 // HTML
  content_json?: object            // TipTap JSON
  status?: PostStatus              // Default: draft
  content_type?: ContentType       // Default: blog_post
  category_id?: string
  author_id?: string
  tag_ids?: string[]
  published_at?: string
  scheduled_at?: string
  meta_title?: string              // Max 70
  meta_description?: string        // Max 160
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  is_featured?: boolean
  allow_comments?: boolean
}
```

### PostResponse

```typescript
interface PostResponse {
  id: string
  title: string
  slug: string
  excerpt?: string
  content?: string
  content_json?: object
  status: PostStatus
  content_type: ContentType
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  word_count?: number
  view_count: number
  is_featured: boolean
  allow_comments: boolean
  version: number
  category?: CategoryResponse
  author?: AuthorResponse
  tags: TagResponse[]
  created_at: string
  updated_at: string
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "POST_NOT_FOUND",
    "message": "Post not found",
    "details": {
      "post_id": "uuid-..."
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `POST_NOT_FOUND` | 404 | Post does not exist |
| `CATEGORY_NOT_FOUND` | 404 | Category does not exist |
| `TAG_NOT_FOUND` | 404 | Tag does not exist |
| `AUTHOR_NOT_FOUND` | 404 | Author does not exist |
| `SLUG_EXISTS` | 409 | Slug already taken |
| `INVALID_STATUS_TRANSITION` | 400 | Invalid workflow transition |
| `PERMISSION_DENIED` | 403 | User lacks permission |
| `POST_LOCKED` | 423 | Post is being edited by another user |
| `VALIDATION_ERROR` | 422 | Request validation failed |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET /posts | 100/min |
| GET /posts/{slug} | 60/min |
| POST /contact | 5/min per IP |
| Admin endpoints | 60/min per user |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
