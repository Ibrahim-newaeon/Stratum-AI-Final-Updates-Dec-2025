# CMS User Flows

## Overview

Step-by-step user journeys for managing content through the CMS, including the 2026 workflow standard for content review and publishing.

---

## Flow 1: Create and Publish a Blog Post

**Actor**: Author / Editor

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREATE & PUBLISH POST                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to CMS Dashboard                                   │
│     └─► /cms/admin/posts                                        │
│                                                                 │
│  2. Click "New Post"                                            │
│     └─► Opens post editor                                       │
│                                                                 │
│  3. Fill in Post Details                                        │
│     ├─► Title: "Introduction to Trust-Gated Automation"        │
│     ├─► Slug: auto-generated or custom                         │
│     ├─► Category: select from dropdown                         │
│     ├─► Author: select or create new                           │
│     ├─► Tags: multi-select                                     │
│     └─► Content Type: blog_post                                │
│                                                                 │
│  4. Write Content                                               │
│     ├─► Use TipTap rich text editor                            │
│     ├─► Add images, links, code blocks                         │
│     └─► Auto-saves draft periodically                          │
│                                                                 │
│  5. Configure SEO                                               │
│     ├─► Meta title (max 70 chars)                              │
│     ├─► Meta description (max 160 chars)                       │
│     └─► Featured image                                         │
│                                                                 │
│  6. Save as Draft                                               │
│     └─► Status: "draft"                                        │
│                                                                 │
│  7. Preview Post                                                │
│     └─► Opens preview mode                                     │
│                                                                 │
│  8. Submit for Review (if Author role)                          │
│     └─► Status: "in_review"                                    │
│     OR                                                          │
│  8. Publish Directly (if Editor+ role)                          │
│     └─► Status: "published"                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Sequence Diagram

```
Author          CMS UI              API              Database
  │                │                  │                  │
  │  Open Editor   │                  │                  │
  │───────────────►│                  │                  │
  │                │ GET /categories  │                  │
  │                │─────────────────►│                  │
  │                │                  │  Query           │
  │                │                  │─────────────────►│
  │                │◄─────────────────│◄─────────────────│
  │                │                  │                  │
  │  Fill content  │                  │                  │
  │───────────────►│                  │                  │
  │                │                  │                  │
  │  Save Draft    │                  │                  │
  │───────────────►│ POST /posts      │                  │
  │                │─────────────────►│                  │
  │                │                  │  Insert          │
  │                │                  │─────────────────►│
  │                │                  │  Create version  │
  │                │                  │─────────────────►│
  │                │◄─────────────────│◄─────────────────│
  │◄───────────────│                  │                  │
  │  Post created  │                  │                  │
  │                │                  │                  │
  │  Submit Review │                  │                  │
  │───────────────►│ POST /{id}/submit│                  │
  │                │─────────────────►│                  │
  │                │                  │  Update status   │
  │                │                  │─────────────────►│
  │                │                  │  Log workflow    │
  │                │                  │─────────────────►│
  │◄───────────────│◄─────────────────│◄─────────────────│
  │                │                  │                  │
```

---

## Flow 2: Editorial Review Process (2026 Workflow)

**Actors**: Author, Reviewer, Editor-in-Chief

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   EDITORIAL REVIEW PROCESS                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AUTHOR:                                                        │
│  1. Create post and submit for review                           │
│     └─► Optionally assign specific reviewer                     │
│                                                                 │
│  REVIEWER:                                                      │
│  2. View posts in review queue                                  │
│     └─► Filter: status = "in_review"                           │
│                                                                 │
│  3. Open post for review                                        │
│     ├─► Read content                                           │
│     ├─► Check SEO fields                                       │
│     └─► Review media/images                                    │
│                                                                 │
│  4. Take Action:                                                │
│     ├─► APPROVE: Status → "approved"                           │
│     │   └─► Can add approval notes                             │
│     │                                                          │
│     ├─► REQUEST CHANGES: Status → "changes_requested"          │
│     │   └─► Must provide change notes                          │
│     │                                                          │
│     └─► REJECT: Status → "rejected"                            │
│         └─► Must provide rejection reason                      │
│                                                                 │
│  AUTHOR (if changes requested):                                 │
│  5. View feedback in workflow history                           │
│                                                                 │
│  6. Make requested changes                                      │
│     └─► New version created automatically                      │
│                                                                 │
│  7. Resubmit for review                                         │
│     └─► Status: "in_review"                                    │
│                                                                 │
│  EDITOR-IN-CHIEF (after approval):                              │
│  8. Publish or schedule approved post                           │
│     ├─► Publish immediately → "published"                      │
│     └─► Schedule for later → "scheduled"                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### State Transitions

```
┌─────────┐ submit    ┌───────────┐ approve   ┌──────────┐
│  DRAFT  │──────────►│ IN_REVIEW │──────────►│ APPROVED │
└─────────┘           └─────┬─────┘           └────┬─────┘
                            │                      │
              request_changes│                     │ publish
                            │                      │
                            ▼                      ▼
                   ┌────────────────┐      ┌───────────┐
                   │CHANGES_REQUESTED│      │ PUBLISHED │
                   └────────┬───────┘      └───────────┘
                            │
                            │ resubmit
                            │
                            ▼
                      ┌───────────┐
                      │ IN_REVIEW │
                      └───────────┘
```

---

## Flow 3: Schedule Content for Future Publishing

**Actor**: Editor / Editor-in-Chief

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULE CONTENT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Create or open approved post                                │
│     └─► Status must be "approved"                              │
│                                                                 │
│  2. Click "Schedule" button                                     │
│                                                                 │
│  3. Select publish date/time                                    │
│     ├─► Date picker opens                                      │
│     ├─► Must be in the future                                  │
│     └─► Timezone displayed                                     │
│                                                                 │
│  4. Confirm scheduling                                          │
│     └─► POST /posts/{id}/schedule?scheduled_at=...             │
│                                                                 │
│  5. System updates status                                       │
│     ├─► Status: "scheduled"                                    │
│     ├─► scheduled_at: selected datetime                        │
│     └─► Workflow log entry created                             │
│                                                                 │
│  6. Celery task monitors scheduled posts                        │
│     └─► Runs every minute                                      │
│                                                                 │
│  7. At scheduled time:                                          │
│     ├─► Status: "published"                                    │
│     ├─► published_at: now()                                    │
│     └─► Post becomes visible                                   │
│                                                                 │
│  OPTIONAL: Unschedule                                           │
│  ─────────────────────                                          │
│  - Click "Unschedule"                                           │
│  - Status returns to "approved"                                 │
│  - scheduled_at cleared                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Scheduler Flow

```
┌─────────────┐
│ Celery Beat │
│ (every min) │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Query posts:     │
│ status=scheduled │
│ scheduled_at ≤   │
│   now()          │
└────────┬─────────┘
         │
         ▼
   ┌───────────┐
   │ For each  │
   │   post    │
   └─────┬─────┘
         │
         ▼
┌──────────────────┐
│ Update:          │
│ status=published │
│ published_at=now │
└──────────────────┘
```

---

## Flow 4: Manage Categories and Tags

**Actor**: Editor-in-Chief / Admin

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   MANAGE CATEGORIES                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to /cms/admin/categories                           │
│                                                                 │
│  2. View existing categories                                    │
│     ├─► Name, slug, color, order                               │
│     └─► Post count per category                                │
│                                                                 │
│  CREATE NEW CATEGORY:                                           │
│  ───────────────────                                            │
│  3. Click "Add Category"                                        │
│                                                                 │
│  4. Fill form:                                                  │
│     ├─► Name: "Engineering"                                    │
│     ├─► Slug: auto-generated "engineering"                     │
│     ├─► Description: optional                                  │
│     ├─► Color: hex picker (#3B82F6)                            │
│     ├─► Icon: select icon                                      │
│     └─► Display order: number                                  │
│                                                                 │
│  5. Save                                                        │
│     └─► POST /admin/categories                                 │
│                                                                 │
│  REORDER CATEGORIES:                                            │
│  ──────────────────                                             │
│  6. Drag-drop to reorder                                        │
│     └─► Updates display_order                                  │
│                                                                 │
│  DEACTIVATE CATEGORY:                                           │
│  ───────────────────                                            │
│  7. Toggle is_active off                                        │
│     └─► Category hidden from public, posts remain              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     MANAGE TAGS                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to /cms/admin/tags                                 │
│                                                                 │
│  2. View tags with usage count                                  │
│                                                                 │
│  3. Create tag:                                                 │
│     ├─► Name: "Machine Learning"                               │
│     ├─► Slug: "machine-learning"                               │
│     └─► Color: optional                                        │
│                                                                 │
│  4. Tags can be:                                                │
│     ├─► Created inline when editing posts                      │
│     ├─► Managed in bulk from tags page                         │
│     └─► Merged (redirect old to new)                           │
│                                                                 │
│  5. Unused tags can be deleted                                  │
│     └─► usage_count = 0                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Manage Authors

**Actor**: Editor-in-Chief / Admin

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                     MANAGE AUTHORS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to /cms/admin/authors                              │
│                                                                 │
│  2. View author list                                            │
│     ├─► Name, avatar, post count                               │
│     └─► Active status                                          │
│                                                                 │
│  CREATE AUTHOR:                                                 │
│  ─────────────                                                  │
│  3. Click "Add Author"                                          │
│                                                                 │
│  4. Fill form:                                                  │
│     ├─► Name: "John Doe"                                       │
│     ├─► Slug: "john-doe"                                       │
│     ├─► Email: john@example.com                                │
│     ├─► Bio: markdown text                                     │
│     ├─► Avatar URL: upload or link                             │
│     ├─► Job Title: "Senior Engineer"                           │
│     └─► Social links: Twitter, LinkedIn, GitHub                │
│                                                                 │
│  5. Link to User (optional)                                     │
│     └─► Select from user dropdown                              │
│     └─► Enables author to edit their own posts                 │
│                                                                 │
│  6. Save                                                        │
│     └─► POST /admin/authors                                    │
│                                                                 │
│  AUTHOR PAGE:                                                   │
│  ───────────                                                    │
│  - Public URL: /blog/authors/{slug}                            │
│  - Shows author bio and all posts by author                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 6: Version Control and Rollback

**Actor**: Editor / Admin

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  VERSION CONTROL                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AUTOMATIC VERSIONING:                                          │
│  ────────────────────                                           │
│  Every content update creates a new version:                    │
│  ├─► Version 1: Initial creation                               │
│  ├─► Version 2: First edit                                     │
│  ├─► Version 3: SEO update                                     │
│  └─► etc.                                                      │
│                                                                 │
│  VIEW VERSION HISTORY:                                          │
│  ────────────────────                                           │
│  1. Open post in editor                                         │
│                                                                 │
│  2. Click "Version History" tab                                 │
│                                                                 │
│  3. View versions list:                                         │
│     ┌──────────────────────────────────────────┐               │
│     │ v3 - SEO update - by John - 2 hours ago  │               │
│     │ v2 - Content fix - by Jane - 1 day ago   │               │
│     │ v1 - Initial - by John - 3 days ago      │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
│  COMPARE VERSIONS:                                              │
│  ────────────────                                               │
│  4. Select two versions to compare                              │
│     └─► Diff view shows changes                                │
│                                                                 │
│  RESTORE VERSION:                                               │
│  ───────────────                                                │
│  5. Click "Restore" on any version                              │
│                                                                 │
│  6. Confirm action                                              │
│     └─► POST /posts/{id}/restore-version/{version}             │
│                                                                 │
│  7. Creates NEW version with old content                        │
│     ├─► Post now at version N+1                                │
│     ├─► Content matches restored version                       │
│     └─► Workflow log: "restored from version X"                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Version Data Stored

| Field | Captured |
|-------|----------|
| title | ✅ |
| slug | ✅ |
| excerpt | ✅ |
| content | ✅ |
| content_json | ✅ |
| meta_title | ✅ |
| meta_description | ✅ |
| featured_image_url | ✅ |
| word_count | ✅ |
| reading_time | ✅ |

---

## Flow 7: Contact Form Management

**Actor**: Admin

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│               CONTACT FORM MANAGEMENT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PUBLIC SUBMISSION:                                             │
│  ─────────────────                                              │
│  1. Visitor fills contact form on landing page                  │
│     ├─► Name (required)                                        │
│     ├─► Email (required)                                       │
│     ├─► Company (optional)                                     │
│     ├─► Phone (optional)                                       │
│     ├─► Subject (optional)                                     │
│     └─► Message (required)                                     │
│                                                                 │
│  2. Form submitted                                              │
│     └─► POST /cms/contact                                      │
│                                                                 │
│  3. System records:                                             │
│     ├─► Submission data                                        │
│     ├─► Source page URL                                        │
│     ├─► IP address                                             │
│     └─► User agent                                             │
│                                                                 │
│  ADMIN MANAGEMENT:                                              │
│  ────────────────                                               │
│  4. Navigate to /cms/admin/contacts                             │
│                                                                 │
│  5. View submissions list                                       │
│     ├─► Filter: unread only                                    │
│     ├─► Filter: exclude spam                                   │
│     └─► Sort by date                                           │
│                                                                 │
│  6. Click submission to view                                    │
│     └─► Automatically marked as read                           │
│                                                                 │
│  7. Take action:                                                │
│     ├─► Mark as responded + add notes                          │
│     ├─► Mark as spam                                           │
│     └─► Delete                                                 │
│                                                                 │
│  SPAM DETECTION:                                                │
│  ──────────────                                                 │
│  - Auto spam_score calculated                                   │
│  - Flagged submissions hidden by default                        │
│  - Manual review available                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 8: Static Page Management

**Actor**: Admin

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  STATIC PAGE MANAGEMENT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to /cms/admin/pages                                │
│                                                                 │
│  2. View pages list:                                            │
│     ├─► About Us                                               │
│     ├─► Terms of Service                                       │
│     ├─► Privacy Policy                                         │
│     └─► Contact                                                │
│                                                                 │
│  CREATE PAGE:                                                   │
│  ───────────                                                    │
│  3. Click "Add Page"                                            │
│                                                                 │
│  4. Fill form:                                                  │
│     ├─► Title: "Terms of Service"                              │
│     ├─► Slug: "terms"                                          │
│     ├─► Content: TipTap editor                                 │
│     ├─► Meta title & description                               │
│     └─► Template: default / wide / sidebar                     │
│                                                                 │
│  NAVIGATION SETTINGS:                                           │
│  ───────────────────                                            │
│  5. Configure navigation:                                       │
│     ├─► Show in navigation: toggle                             │
│     ├─► Navigation label: "Terms"                              │
│     └─► Navigation order: 1, 2, 3...                           │
│                                                                 │
│  6. Save and publish                                            │
│     ├─► Status: draft → published                              │
│     └─► Public URL: /terms                                     │
│                                                                 │
│  FOOTER LINKS:                                                  │
│  ────────────                                                   │
│  - Pages with show_in_navigation appear in footer              │
│  - Ordered by navigation_order                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 9: Workflow History and Audit

**Actor**: Editor / Admin

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   WORKFLOW HISTORY                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Open post in editor                                         │
│                                                                 │
│  2. Click "Workflow History" tab                                │
│                                                                 │
│  3. View complete audit trail:                                  │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ Jan 15, 14:30 - PUBLISHED                            │   │
│     │   by Sarah (editor_in_chief)                         │   │
│     │   draft → published                                  │   │
│     ├──────────────────────────────────────────────────────┤   │
│     │ Jan 15, 11:00 - APPROVED                             │   │
│     │   by Mike (reviewer)                                 │   │
│     │   "Good to go, minor fixes applied"                  │   │
│     │   in_review → approved                               │   │
│     ├──────────────────────────────────────────────────────┤   │
│     │ Jan 14, 16:45 - SUBMITTED_FOR_REVIEW                 │   │
│     │   by John (author)                                   │   │
│     │   draft → in_review                                  │   │
│     ├──────────────────────────────────────────────────────┤   │
│     │ Jan 14, 14:00 - UPDATED (v2)                         │   │
│     │   by John (author)                                   │   │
│     │   "Fixed typos in introduction"                      │   │
│     ├──────────────────────────────────────────────────────┤   │
│     │ Jan 12, 10:00 - CREATED (v1)                         │   │
│     │   by John (author)                                   │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  FILTER OPTIONS:                                                │
│  ──────────────                                                 │
│  - By action type                                               │
│  - By user                                                      │
│  - By date range                                                │
│                                                                 │
│  EXPORT AUDIT LOG:                                              │
│  ────────────────                                               │
│  - Download as CSV for compliance                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
