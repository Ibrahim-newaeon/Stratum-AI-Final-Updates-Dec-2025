# CMS Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Content Management System.

---

## Edge Cases

### 1. Duplicate Slug

**Scenario**: Creating a post/page with a slug that already exists.

**Behavior**:
- Validation error returned
- HTTP 409 Conflict
- Suggested alternative slug provided

**Response**:
```json
{
  "error": {
    "code": "SLUG_EXISTS",
    "message": "Slug 'my-post' already exists",
    "details": {
      "existing_slug": "my-post",
      "suggested_slug": "my-post-2"
    }
  }
}
```

**Handling**:
```python
def generate_unique_slug(base_slug: str) -> str:
    slug = base_slug
    counter = 2
    while await slug_exists(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug
```

---

### 2. Invalid Workflow Transition

**Scenario**: Attempting an invalid status transition (e.g., draft → published without approval).

**Behavior**:
- Transition rejected
- HTTP 400 Bad Request
- Valid transitions listed in error

**Valid Transitions**:
| From | To |
|------|-----|
| draft | in_review, published*, scheduled* |
| in_review | approved, rejected, changes_requested |
| changes_requested | in_review |
| approved | published, scheduled |
| scheduled | published |
| published | unpublished, archived |
| unpublished | published, archived |
| rejected | in_review (resubmit) |

*Direct publish/schedule requires Editor-in-Chief+ role

**Response**:
```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Cannot transition from 'draft' to 'published'",
    "details": {
      "current_status": "draft",
      "requested_status": "published",
      "valid_transitions": ["in_review"],
      "requires_role": "editor_in_chief"
    }
  }
}
```

---

### 3. Post Locked for Editing

**Scenario**: Two users try to edit the same post simultaneously.

**Behavior**:
- First user acquires lock
- Lock expires after 5 minutes of inactivity
- Second user sees lock warning

**Locking Flow**:
```python
async def acquire_edit_lock(post_id: UUID, user_id: int) -> bool:
    post = await get_post(post_id)

    if post.locked_by_id and post.locked_by_id != user_id:
        # Check if lock is stale (> 5 minutes)
        if post.locked_at and (now() - post.locked_at) < timedelta(minutes=5):
            raise PostLockedException(post.locked_by_id)

    post.locked_by_id = user_id
    post.locked_at = now()
    await db.commit()
    return True
```

**Response**:
```json
{
  "error": {
    "code": "POST_LOCKED",
    "message": "Post is being edited by another user",
    "details": {
      "locked_by_user_id": 456,
      "locked_at": "2024-01-15T14:25:00Z",
      "lock_expires_at": "2024-01-15T14:30:00Z"
    }
  }
}
```

---

### 4. Scheduled Post Time in Past

**Scenario**: Attempting to schedule a post for a past datetime.

**Behavior**:
- Validation error
- Suggestion to publish immediately instead

**Response**:
```json
{
  "error": {
    "code": "INVALID_SCHEDULE_TIME",
    "message": "Scheduled time must be in the future",
    "details": {
      "requested_time": "2024-01-10T10:00:00Z",
      "current_time": "2024-01-15T14:00:00Z",
      "suggestion": "Use /publish endpoint for immediate publishing"
    }
  }
}
```

---

### 5. Category Deletion with Posts

**Scenario**: Deleting a category that has associated posts.

**Behavior**:
- Category deleted successfully
- Posts have `category_id` set to NULL
- Posts remain in system, just uncategorized

**Warning Response**:
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "category_id": "uuid-...",
    "posts_affected": 12,
    "warning": "12 posts are now uncategorized"
  }
}
```

---

### 6. Author Deletion with Posts

**Scenario**: Deleting an author who has written posts.

**Behavior**:
- Author deleted (soft delete)
- Posts keep reference to author_id
- Author displays as "Deleted Author" on posts

**Response**:
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "author_id": "uuid-...",
    "posts_affected": 25
  }
}
```

---

### 7. Tag Usage Count Desync

**Scenario**: Tag's `usage_count` doesn't match actual post count.

**Cause**: Race condition during concurrent tag operations.

**Recovery**:
```python
async def recalculate_tag_usage():
    """Periodic job to fix usage counts."""
    await db.execute("""
        UPDATE cms_tags SET usage_count = (
            SELECT COUNT(*) FROM cms_post_tags
            WHERE tag_id = cms_tags.id
        )
    """)
```

---

### 8. Version Restore Conflict

**Scenario**: Restoring a version that references a deleted category/author.

**Behavior**:
- Content restored successfully
- Foreign key references validated
- Missing references set to NULL

**Handling**:
```python
async def restore_version(post_id: UUID, version: int):
    version_data = await get_version(post_id, version)

    # Validate category still exists
    if version_data.category_id:
        category = await get_category(version_data.category_id)
        if not category:
            version_data.category_id = None

    # Apply restoration
    await update_post(post_id, version_data)
```

---

### 9. Large Content Upload

**Scenario**: Post content exceeds reasonable size limits.

**Limits**:
| Field | Max Size |
|-------|----------|
| content | 500 KB |
| content_json | 1 MB |
| Total request | 2 MB |

**Response**:
```json
{
  "error": {
    "code": "CONTENT_TOO_LARGE",
    "message": "Content exceeds maximum size",
    "details": {
      "content_size": "750KB",
      "max_allowed": "500KB"
    }
  }
}
```

---

### 10. Concurrent Workflow Actions

**Scenario**: Two reviewers approve/reject the same post simultaneously.

**Behavior**:
- First action succeeds
- Second action fails with conflict
- Optimistic locking via version number

**Handling**:
```python
async def approve_post(post_id: UUID, user_id: int, expected_status: str):
    post = await get_post(post_id)

    if post.status != expected_status:
        raise WorkflowConflictException(
            f"Post status changed to {post.status}"
        )

    post.status = "approved"
    await db.commit()
```

---

### 11. SEO Field Truncation

**Scenario**: User provides meta_title or meta_description exceeding limits.

**Behavior**:
- Automatic truncation with ellipsis
- Warning returned in response

**Truncation**:
```python
def truncate_seo_field(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[:max_length-3] + "..."
```

**Response**:
```json
{
  "success": true,
  "data": { ... },
  "warnings": [
    "meta_title truncated from 85 to 70 characters"
  ]
}
```

---

### 12. Scheduled Post Scheduler Failure

**Scenario**: Scheduler fails to publish scheduled post at scheduled time.

**Behavior**:
- Post remains in "scheduled" status
- Next scheduler run publishes it
- Delay recorded in logs

**Monitoring**:
```python
async def publish_scheduled_posts():
    overdue = await db.execute(
        select(CMSPost).where(
            CMSPost.status == "scheduled",
            CMSPost.scheduled_at <= datetime.utcnow()
        )
    )

    for post in overdue:
        delay = datetime.utcnow() - post.scheduled_at
        if delay > timedelta(minutes=5):
            logger.warning(f"Post {post.id} published {delay} late")

        await publish_post(post)
```

---

### 13. Contact Form Spam Flood

**Scenario**: Bot submits many contact forms rapidly.

**Mitigation**:
- Rate limiting: 5/min per IP
- Honeypot field detection
- Spam score calculation

**Spam Detection**:
```python
def calculate_spam_score(submission) -> int:
    score = 0

    # Check for common spam patterns
    if "http" in submission.message.lower():
        score += 20
    if any(word in submission.message.lower() for word in SPAM_WORDS):
        score += 30
    if submission.honeypot_field:  # Hidden field filled
        score += 100

    return min(score, 100)
```

---

### 14. Image URL Validation

**Scenario**: Featured image URL returns 404 or is malformed.

**Behavior**:
- URL format validated on save
- Async check for image accessibility
- Warning if image not reachable

**Validation**:
```python
async def validate_image_url(url: str) -> dict:
    try:
        response = await http_client.head(url)
        return {
            "valid": response.status_code == 200,
            "content_type": response.headers.get("content-type"),
            "status": response.status_code
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
```

---

### 15. Workflow History Retention

**Scenario**: Post has extensive workflow history (100+ entries).

**Behavior**:
- History paginated
- Older entries archived after 1 year
- Summary statistics available

**Pagination**:
```json
{
  "history": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "summary": {
    "total_revisions": 45,
    "total_reviews": 12,
    "average_review_time_hours": 8.5
  }
}
```

---

## Known Limitations

### 1. Real-time Collaboration

**Limitation**: No real-time collaborative editing.

**Workaround**: Edit lock system prevents conflicts. Only one user can edit at a time.

---

### 2. Content Versioning Storage

**Limitation**: All versions stored indefinitely.

**Impact**: Large posts with many revisions consume storage.

**Planned**: Version pruning policy (keep last 50 versions).

---

### 3. Search Scope

**Limitation**: Search only queries title and excerpt, not full content.

**Reason**: Full-text search requires additional infrastructure.

**Planned**: Elasticsearch integration for full-text search.

---

### 4. Image Management

**Limitation**: CMS doesn't manage images directly.

**Current**: External CDN URLs used for images.

**Planned**: Integrated media library with upload functionality.

---

### 5. Preview Limitations

**Limitation**: Preview shows content only, not full site styling.

**Workaround**: Preview in new tab with draft token.

---

## Error Recovery

### Workflow Errors

| Error | Recovery |
|-------|----------|
| Invalid transition | Check current status, use valid transition |
| Permission denied | Contact admin for role upgrade |
| Post locked | Wait for lock expiry or contact lock holder |

### Data Errors

| Error | Recovery |
|-------|----------|
| Slug conflict | Choose different slug or auto-generate |
| Missing category | Reassign or leave uncategorized |
| Missing author | Create new author or leave unassigned |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Scheduled post delay | > 5 minutes |
| Edit lock timeout rate | > 10% |
| Contact form spam rate | > 30% |
| Version storage growth | > 1GB/month |

### Health Checks

```python
async def cms_health() -> dict:
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db_connection(),
            "scheduler": await check_scheduler_running(),
            "recent_posts": await count_recent_posts(hours=24),
            "pending_scheduled": await count_scheduled_posts()
        }
    }
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
