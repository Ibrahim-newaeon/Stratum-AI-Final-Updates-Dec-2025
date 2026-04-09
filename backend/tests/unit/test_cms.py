# =============================================================================
# Stratum AI - CMS Feature Test Suite
# =============================================================================
"""
Comprehensive tests for the CMS feature (Feature #9):

1. CMS Enums (CMSPostStatus, CMSContentType, CMSPageStatus, CMSWorkflowAction)
2. CMS Model methods (soft_delete, submit_for_review, approve, reject, etc.)
3. CMS Endpoint helpers (slugify, calculate_reading_time, count_words, check_cms_permission)
4. CMS Pydantic schemas (validation, field constraints, custom validators)
5. CDN cache invalidation logic (_invalidate_cdn_cache, per-provider purge)

Note: RBAC permission matrix is tested in test_cms_rbac.py (existing).
"""

import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.cms import (
    calculate_reading_time,
    check_cms_permission,
    count_words,
    slugify,
)
from app.models.cms import (
    CMSContentType,
    CMSPage,
    CMSPageStatus,
    CMSPost,
    CMSPostStatus,
    CMSRole,
    CMSWorkflowAction,
)
from app.schemas.cms import (
    CategoryCreate,
    CategoryUpdate,
    CMSAssignRoleRequest,
    CMSInviteUserRequest,
    CMSUpdateRoleRequest,
    ContactMarkRead,
    ContactMarkResponded,
    ContactMarkSpam,
    ContactSubmit,
    PageCreate,
    PageUpdate,
    PostCreate,
    PostUpdate,
    TagCreate,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_post(**overrides) -> CMSPost:
    """Create a CMSPost instance without DB using the constructor."""
    defaults = dict(
        title="Test Post",
        slug="test-post",
        content="<p>Hello world</p>",
        status=CMSPostStatus.DRAFT.value,
        content_type=CMSContentType.BLOG_POST.value,
        version=1,
        view_count=0,
        is_featured=False,
        allow_comments=True,
        is_deleted=False,
    )
    defaults.update(overrides)
    return CMSPost(**defaults)


def _make_page(**overrides) -> CMSPage:
    """Create a CMSPage instance without DB."""
    defaults = dict(
        title="About Us",
        slug="about-us",
        content="<p>About page content</p>",
        status=CMSPageStatus.DRAFT.value,
        is_deleted=False,
    )
    defaults.update(overrides)
    return CMSPage(**defaults)


# #############################################################################
#
#  PART 1: CMS ENUMS
#
# #############################################################################


@pytest.mark.unit
class TestCMSPostStatus:

    def test_all_statuses_present(self) -> None:
        expected = {
            "draft", "in_review", "changes_requested", "approved",
            "scheduled", "published", "unpublished", "archived", "rejected",
        }
        assert {s.value for s in CMSPostStatus} == expected

    def test_enum_count(self) -> None:
        assert len(CMSPostStatus) == 9

    def test_string_enum_type(self) -> None:
        assert isinstance(CMSPostStatus.DRAFT, str)
        assert CMSPostStatus.DRAFT == "draft"

    def test_construction_from_value(self) -> None:
        assert CMSPostStatus("published") == CMSPostStatus.PUBLISHED


@pytest.mark.unit
class TestCMSContentType:

    def test_all_types_present(self) -> None:
        expected = {
            "blog_post", "case_study", "guide", "whitepaper",
            "announcement", "newsletter", "press_release",
        }
        assert {t.value for t in CMSContentType} == expected

    def test_enum_count(self) -> None:
        assert len(CMSContentType) == 7

    def test_string_type(self) -> None:
        assert CMSContentType.BLOG_POST == "blog_post"

    def test_construction(self) -> None:
        assert CMSContentType("case_study") == CMSContentType.CASE_STUDY


@pytest.mark.unit
class TestCMSPageStatus:

    def test_all_statuses(self) -> None:
        expected = {"draft", "in_review", "approved", "published", "archived"}
        assert {s.value for s in CMSPageStatus} == expected

    def test_enum_count(self) -> None:
        assert len(CMSPageStatus) == 5


@pytest.mark.unit
class TestCMSWorkflowAction:

    def test_all_actions(self) -> None:
        expected = {
            "created", "updated", "submitted_for_review", "approved",
            "rejected", "changes_requested", "scheduled", "published",
            "unpublished", "archived", "restored", "deleted",
        }
        assert {a.value for a in CMSWorkflowAction} == expected

    def test_enum_count(self) -> None:
        assert len(CMSWorkflowAction) == 12


# #############################################################################
#
#  PART 2: CMS MODEL METHODS
#
# #############################################################################


@pytest.mark.unit
class TestCMSPostMethods:

    def test_soft_delete(self) -> None:
        post = _make_post()
        assert post.is_deleted is False
        assert post.deleted_at is None

        post.soft_delete()

        assert post.is_deleted is True
        assert post.deleted_at is not None
        assert isinstance(post.deleted_at, datetime)

    def test_submit_for_review(self) -> None:
        post = _make_post(status=CMSPostStatus.DRAFT.value)

        post.submit_for_review(user_id=42)

        assert post.status == CMSPostStatus.IN_REVIEW.value
        assert post.submitted_at is not None
        assert post.submitted_by_id == 42

    def test_approve_without_notes(self) -> None:
        post = _make_post(status=CMSPostStatus.IN_REVIEW.value)

        post.approve(user_id=10)

        assert post.status == CMSPostStatus.APPROVED.value
        assert post.approved_at is not None
        assert post.approved_by_id == 10
        assert post.reviewed_at is not None
        assert post.reviewed_by_id == 10
        assert post.review_notes is None

    def test_approve_with_notes(self) -> None:
        post = _make_post(status=CMSPostStatus.IN_REVIEW.value)

        post.approve(user_id=10, notes="Looks great!")

        assert post.review_notes == "Looks great!"

    def test_reject(self) -> None:
        post = _make_post(status=CMSPostStatus.IN_REVIEW.value)

        post.reject(user_id=5, reason="Needs more research")

        assert post.status == CMSPostStatus.REJECTED.value
        assert post.rejected_at is not None
        assert post.rejected_by_id == 5
        assert post.rejection_reason == "Needs more research"
        assert post.reviewed_at is not None
        assert post.reviewed_by_id == 5

    def test_request_changes(self) -> None:
        post = _make_post(status=CMSPostStatus.IN_REVIEW.value)

        post.request_changes(user_id=7, notes="Fix the intro paragraph")

        assert post.status == CMSPostStatus.CHANGES_REQUESTED.value
        assert post.reviewed_at is not None
        assert post.reviewed_by_id == 7
        assert post.review_notes == "Fix the intro paragraph"

    def test_publish(self) -> None:
        post = _make_post(status=CMSPostStatus.APPROVED.value)

        post.publish()

        assert post.status == CMSPostStatus.PUBLISHED.value
        assert post.published_at is not None
        assert isinstance(post.published_at, datetime)

    def test_schedule(self) -> None:
        post = _make_post(status=CMSPostStatus.APPROVED.value)
        future = datetime.now(UTC) + timedelta(days=3)

        post.schedule(publish_at=future)

        assert post.status == CMSPostStatus.SCHEDULED.value
        assert post.scheduled_at == future

    def test_repr(self) -> None:
        post = _make_post(title="My Post", status="draft", version=2)
        r = repr(post)
        assert "My Post" in r
        assert "draft" in r
        assert "v2" in r

    def test_workflow_submit_then_approve_then_publish(self) -> None:
        """Full workflow: draft -> in_review -> approved -> published."""
        post = _make_post()
        assert post.status == CMSPostStatus.DRAFT.value

        post.submit_for_review(user_id=1)
        assert post.status == CMSPostStatus.IN_REVIEW.value

        post.approve(user_id=2)
        assert post.status == CMSPostStatus.APPROVED.value

        post.publish()
        assert post.status == CMSPostStatus.PUBLISHED.value

    def test_workflow_submit_then_reject(self) -> None:
        """Workflow: draft -> in_review -> rejected."""
        post = _make_post()
        post.submit_for_review(user_id=1)
        post.reject(user_id=2, reason="Off-topic")
        assert post.status == CMSPostStatus.REJECTED.value

    def test_workflow_submit_request_changes_resubmit(self) -> None:
        """Workflow: submit -> changes requested -> re-submit."""
        post = _make_post()
        post.submit_for_review(user_id=1)
        post.request_changes(user_id=2, notes="Fix typo")
        assert post.status == CMSPostStatus.CHANGES_REQUESTED.value

        # Author fixes and re-submits
        post.submit_for_review(user_id=1)
        assert post.status == CMSPostStatus.IN_REVIEW.value

    def test_workflow_approve_then_schedule(self) -> None:
        """Workflow: approved -> scheduled."""
        post = _make_post()
        post.submit_for_review(user_id=1)
        post.approve(user_id=2)
        future = datetime.now(UTC) + timedelta(hours=6)
        post.schedule(publish_at=future)
        assert post.status == CMSPostStatus.SCHEDULED.value
        assert post.scheduled_at == future


@pytest.mark.unit
class TestCMSPageMethods:

    def test_soft_delete(self) -> None:
        page = _make_page()
        assert page.is_deleted is False
        page.soft_delete()
        assert page.is_deleted is True
        assert page.deleted_at is not None

    def test_repr(self) -> None:
        page = _make_page(title="About", status="draft")
        r = repr(page)
        assert "About" in r
        assert "draft" in r


# #############################################################################
#
#  PART 3: ENDPOINT HELPERS
#
# #############################################################################


@pytest.mark.unit
class TestSlugify:

    def test_basic_text(self) -> None:
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self) -> None:
        assert slugify("What's New in 2026?") == "whats-new-in-2026"

    def test_leading_trailing_spaces(self) -> None:
        assert slugify("  Padded Title  ") == "padded-title"

    def test_multiple_spaces(self) -> None:
        assert slugify("Multiple   Spaces   Here") == "multiple-spaces-here"

    def test_hyphens_preserved(self) -> None:
        assert slugify("already-slugified") == "already-slugified"

    def test_mixed_case(self) -> None:
        assert slugify("CamelCase Title") == "camelcase-title"

    def test_unicode_removed(self) -> None:
        result = slugify("Café & Bar!")
        assert "caf" in result
        assert "&" not in result

    def test_empty_slug_not_generated(self) -> None:
        # Special chars only produce empty string
        result = slugify("!@#$%")
        assert result == ""

    def test_numbers_preserved(self) -> None:
        assert slugify("Top 10 Tips") == "top-10-tips"


@pytest.mark.unit
class TestCalculateReadingTime:

    def test_none_content(self) -> None:
        assert calculate_reading_time(None) is None

    def test_empty_content(self) -> None:
        assert calculate_reading_time("") is None

    def test_short_content_minimum_one_minute(self) -> None:
        # A few words = still 1 minute minimum
        assert calculate_reading_time("Hello world") == 1

    def test_exact_200_words(self) -> None:
        content = " ".join(["word"] * 200)
        assert calculate_reading_time(content) == 1

    def test_400_words(self) -> None:
        content = " ".join(["word"] * 400)
        assert calculate_reading_time(content) == 2

    def test_1000_words(self) -> None:
        content = " ".join(["word"] * 1000)
        assert calculate_reading_time(content) == 5

    def test_html_content_counts_words(self) -> None:
        content = "<p>This is a paragraph with <strong>bold</strong> text</p>"
        result = calculate_reading_time(content)
        assert result == 1  # ~10 words = 1 min


@pytest.mark.unit
class TestCountWords:

    def test_none_content(self) -> None:
        assert count_words(None) is None

    def test_empty_content(self) -> None:
        assert count_words("") is None

    def test_simple_text(self) -> None:
        assert count_words("Hello world foo bar") == 4

    def test_html_content(self) -> None:
        # \w+ matches tag names too: p, One, two, three, p = 5
        assert count_words("<p>One two three</p>") == 5

    def test_single_word(self) -> None:
        assert count_words("hello") == 1


@pytest.mark.unit
class TestCheckCMSPermission:

    @pytest.mark.asyncio
    async def test_superadmin_fallback(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role=None, role="superadmin")
        assert await check_cms_permission(request, "publish_post") is True

    @pytest.mark.asyncio
    async def test_no_role_no_cms_role(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role=None, role="viewer")
        assert await check_cms_permission(request, "publish_post") is False

    @pytest.mark.asyncio
    async def test_cms_super_admin(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="super_admin")
        assert await check_cms_permission(request, "publish_post") is True

    @pytest.mark.asyncio
    async def test_cms_viewer_cannot_publish(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="viewer")
        assert await check_cms_permission(request, "publish_post") is False

    @pytest.mark.asyncio
    async def test_cms_editor_can_schedule(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="editor")
        assert await check_cms_permission(request, "schedule_post") is True

    @pytest.mark.asyncio
    async def test_invalid_cms_role_returns_false(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="nonexistent_role")
        assert await check_cms_permission(request, "publish_post") is False

    @pytest.mark.asyncio
    async def test_author_can_submit_for_review(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="author")
        assert await check_cms_permission(request, "submit_for_review") is True

    @pytest.mark.asyncio
    async def test_contributor_cannot_submit_for_review(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="contributor")
        assert await check_cms_permission(request, "submit_for_review") is False

    @pytest.mark.asyncio
    async def test_reviewer_can_approve(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="reviewer")
        assert await check_cms_permission(request, "approve_post") is True

    @pytest.mark.asyncio
    async def test_reviewer_cannot_create(self) -> None:
        request = MagicMock()
        request.state = SimpleNamespace(cms_role="reviewer")
        assert await check_cms_permission(request, "create_post") is False


# #############################################################################
#
#  PART 4: PYDANTIC SCHEMA VALIDATION
#
# #############################################################################


@pytest.mark.unit
class TestPostCreateSchema:

    def test_minimal_valid(self) -> None:
        post = PostCreate(title="My Post")
        assert post.title == "My Post"
        assert post.status == "draft"
        assert post.content_type == "blog_post"

    def test_valid_status_values(self) -> None:
        for s in ("draft", "scheduled", "published", "archived"):
            post = PostCreate(title="T", status=s)
            assert post.status == s

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid status"):
            PostCreate(title="T", status="deleted")

    def test_status_case_insensitive(self) -> None:
        post = PostCreate(title="T", status="DRAFT")
        assert post.status == "draft"

    def test_valid_content_types(self) -> None:
        for ct in ("blog_post", "case_study", "guide", "whitepaper", "announcement"):
            post = PostCreate(title="T", content_type=ct)
            assert post.content_type == ct

    def test_invalid_content_type_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid content type"):
            PostCreate(title="T", content_type="video")

    def test_content_type_case_insensitive(self) -> None:
        post = PostCreate(title="T", content_type="GUIDE")
        assert post.content_type == "guide"

    def test_meta_title_max_length(self) -> None:
        post = PostCreate(title="T", meta_title="A" * 70)
        assert len(post.meta_title) == 70
        with pytest.raises(ValidationError):
            PostCreate(title="T", meta_title="A" * 71)

    def test_meta_description_max_length(self) -> None:
        post = PostCreate(title="T", meta_description="A" * 160)
        assert len(post.meta_description) == 160
        with pytest.raises(ValidationError):
            PostCreate(title="T", meta_description="A" * 161)

    def test_title_required(self) -> None:
        with pytest.raises(ValidationError):
            PostCreate()

    def test_title_min_length(self) -> None:
        with pytest.raises(ValidationError):
            PostCreate(title="")

    def test_reading_time_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PostCreate(title="T", reading_time_minutes=0)

    def test_tag_ids_default_empty(self) -> None:
        post = PostCreate(title="T")
        assert post.tag_ids == []

    def test_is_featured_default_false(self) -> None:
        post = PostCreate(title="T")
        assert post.is_featured is False

    def test_allow_comments_default_true(self) -> None:
        post = PostCreate(title="T")
        assert post.allow_comments is True


@pytest.mark.unit
class TestPostUpdateSchema:

    def test_all_optional(self) -> None:
        update = PostUpdate()
        assert update.title is None
        assert update.status is None

    def test_valid_status_update(self) -> None:
        update = PostUpdate(status="published")
        assert update.status == "published"

    def test_invalid_status_update(self) -> None:
        with pytest.raises(ValidationError, match="Invalid status"):
            PostUpdate(status="in_review")

    def test_none_status_allowed(self) -> None:
        update = PostUpdate(status=None)
        assert update.status is None

    def test_content_type_update_valid(self) -> None:
        update = PostUpdate(content_type="case_study")
        assert update.content_type == "case_study"

    def test_content_type_update_invalid(self) -> None:
        with pytest.raises(ValidationError, match="Invalid content type"):
            PostUpdate(content_type="podcast")


@pytest.mark.unit
class TestPageCreateSchema:

    def test_minimal_valid(self) -> None:
        page = PageCreate(title="About")
        assert page.title == "About"
        assert page.status == "draft"
        assert page.template == "default"

    def test_valid_status_values(self) -> None:
        for s in ("draft", "published", "archived"):
            page = PageCreate(title="T", status=s)
            assert page.status == s

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError, match="Invalid status"):
            PageCreate(title="T", status="in_review")

    def test_navigation_defaults(self) -> None:
        page = PageCreate(title="T")
        assert page.show_in_navigation is False
        assert page.navigation_order == 0

    def test_meta_fields(self) -> None:
        page = PageCreate(title="T", meta_title="SEO Title", meta_description="SEO Desc")
        assert page.meta_title == "SEO Title"


@pytest.mark.unit
class TestPageUpdateSchema:

    def test_all_optional(self) -> None:
        update = PageUpdate()
        assert update.title is None

    def test_valid_status(self) -> None:
        update = PageUpdate(status="published")
        assert update.status == "published"

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError, match="Invalid status"):
            PageUpdate(status="rejected")

    def test_none_status_allowed(self) -> None:
        update = PageUpdate(status=None)
        assert update.status is None


@pytest.mark.unit
class TestCategorySchemas:

    def test_create_minimal(self) -> None:
        cat = CategoryCreate(name="Engineering")
        assert cat.name == "Engineering"
        assert cat.display_order == 0
        assert cat.is_active is True

    def test_create_with_color(self) -> None:
        cat = CategoryCreate(name="T", color="#FF5500")
        assert cat.color == "#FF5500"

    def test_create_invalid_color(self) -> None:
        with pytest.raises(ValidationError):
            CategoryCreate(name="T", color="red")

    def test_create_name_required(self) -> None:
        with pytest.raises(ValidationError):
            CategoryCreate()

    def test_update_all_optional(self) -> None:
        update = CategoryUpdate()
        assert update.name is None


@pytest.mark.unit
class TestTagSchemas:

    def test_create_minimal(self) -> None:
        tag = TagCreate(name="Python")
        assert tag.name == "Python"

    def test_name_max_length(self) -> None:
        tag = TagCreate(name="A" * 50)
        assert len(tag.name) == 50
        with pytest.raises(ValidationError):
            TagCreate(name="A" * 51)


@pytest.mark.unit
class TestContactSchemas:

    def test_submit_minimal(self) -> None:
        contact = ContactSubmit(
            name="John", email="john@example.com",
            message="Hello, I'd like to know more about your services.",
        )
        assert contact.name == "John"
        assert contact.company is None
        assert contact.phone is None

    def test_submit_message_min_length(self) -> None:
        with pytest.raises(ValidationError):
            ContactSubmit(name="John", email="john@test.com", message="Short")

    def test_submit_message_max_length(self) -> None:
        with pytest.raises(ValidationError):
            ContactSubmit(name="J", email="j@t.com", message="A" * 5001)

    def test_submit_name_required(self) -> None:
        with pytest.raises(ValidationError):
            ContactSubmit(email="j@t.com", message="Hello world testing.")

    def test_submit_email_required(self) -> None:
        with pytest.raises(ValidationError):
            ContactSubmit(name="John", message="Hello world testing.")

    def test_mark_read_defaults(self) -> None:
        m = ContactMarkRead()
        assert m.is_read is True

    def test_mark_responded_defaults(self) -> None:
        m = ContactMarkResponded()
        assert m.is_responded is True
        assert m.response_notes is None

    def test_mark_spam_defaults(self) -> None:
        m = ContactMarkSpam()
        assert m.is_spam is True


@pytest.mark.unit
class TestCMSRoleSchemas:

    def test_assign_role_valid(self) -> None:
        req = CMSAssignRoleRequest(user_id=1, cms_role="editor")
        assert req.cms_role == "editor"

    def test_assign_role_invalid(self) -> None:
        with pytest.raises(ValidationError, match="Invalid CMS role"):
            CMSAssignRoleRequest(user_id=1, cms_role="boss")

    def test_update_role_valid(self) -> None:
        req = CMSUpdateRoleRequest(cms_role="author")
        assert req.cms_role == "author"

    def test_update_role_invalid(self) -> None:
        with pytest.raises(ValidationError, match="Invalid CMS role"):
            CMSUpdateRoleRequest(cms_role="supreme_leader")

    def test_invite_user_valid(self) -> None:
        req = CMSInviteUserRequest(
            email="new@test.com", full_name="New User",
            password="SecurePass123", cms_role="contributor",
        )
        assert req.cms_role == "contributor"

    def test_invite_user_invalid_role(self) -> None:
        with pytest.raises(ValidationError, match="Invalid CMS role"):
            CMSInviteUserRequest(
                email="new@test.com", full_name="New",
                password="SecurePass123", cms_role="invalid",
            )

    def test_invite_user_password_min_length(self) -> None:
        with pytest.raises(ValidationError):
            CMSInviteUserRequest(
                email="new@test.com", full_name="New",
                password="short", cms_role="viewer",
            )

    def test_all_valid_cms_roles(self) -> None:
        for role in CMSRole:
            req = CMSAssignRoleRequest(user_id=1, cms_role=role.value)
            assert req.cms_role == role.value


# #############################################################################
#
#  PART 5: CDN CACHE INVALIDATION
#
# #############################################################################


@pytest.mark.unit
class TestCDNInvalidation:

    def test_no_cdn_provider_returns_silently(self) -> None:
        from app.workers.tasks.cms import _invalidate_cdn_cache

        post = MagicMock()
        post.slug = "test-post"

        mock_settings = MagicMock()
        mock_settings.cdn_provider = None

        with patch("app.core.config.settings", mock_settings):
            _invalidate_cdn_cache(post)

    def test_cloudflare_provider_calls_purge(self) -> None:
        from app.workers.tasks.cms import _invalidate_cdn_cache

        post = MagicMock()
        post.slug = "test-post"

        mock_settings = MagicMock()
        mock_settings.cdn_provider = "cloudflare"

        with patch("app.core.config.settings", mock_settings), \
             patch("app.workers.tasks.cms._purge_cloudflare") as mock_purge:
            _invalidate_cdn_cache(post)
            mock_purge.assert_called_once()
            paths = mock_purge.call_args[0][0]
            assert "/blog/test-post" in paths
            assert "/sitemap.xml" in paths

    def test_cloudfront_provider_calls_purge(self) -> None:
        from app.workers.tasks.cms import _invalidate_cdn_cache

        post = MagicMock()
        post.slug = "my-article"

        mock_settings = MagicMock()
        mock_settings.cdn_provider = "cloudfront"

        with patch("app.core.config.settings", mock_settings), \
             patch("app.workers.tasks.cms._purge_cloudfront") as mock_purge:
            _invalidate_cdn_cache(post)
            mock_purge.assert_called_once()

    def test_fastly_provider_calls_purge(self) -> None:
        from app.workers.tasks.cms import _invalidate_cdn_cache

        post = MagicMock()
        post.slug = "news-update"

        mock_settings = MagicMock()
        mock_settings.cdn_provider = "fastly"

        with patch("app.core.config.settings", mock_settings), \
             patch("app.workers.tasks.cms._purge_fastly") as mock_purge:
            _invalidate_cdn_cache(post)
            mock_purge.assert_called_once()

    def test_purge_failure_does_not_raise(self) -> None:
        from app.workers.tasks.cms import _invalidate_cdn_cache

        post = MagicMock()
        post.slug = "test"

        mock_settings = MagicMock()
        mock_settings.cdn_provider = "cloudflare"

        with patch("app.core.config.settings", mock_settings), \
             patch("app.workers.tasks.cms._purge_cloudflare", side_effect=ConnectionError("down")):
            # Should log warning but not raise
            _invalidate_cdn_cache(post)

    def test_cache_paths_include_blog_and_api(self) -> None:
        from app.workers.tasks.cms import _invalidate_cdn_cache

        post = MagicMock()
        post.slug = "featured-article"

        mock_settings = MagicMock()
        mock_settings.cdn_provider = "cloudflare"

        with patch("app.core.config.settings", mock_settings), \
             patch("app.workers.tasks.cms._purge_cloudflare") as mock_purge:
            _invalidate_cdn_cache(post)
            paths = mock_purge.call_args[0][0]
            assert len(paths) == 4
            assert "/blog/featured-article" in paths
            assert "/api/v1/cms/posts/featured-article" in paths
            assert "/blog" in paths
            assert "/sitemap.xml" in paths


@pytest.mark.unit
class TestCloudflare:

    def test_skips_without_credentials(self) -> None:
        from app.workers.tasks.cms import _purge_cloudflare

        mock_settings = MagicMock()
        mock_settings.cdn_api_key = None
        mock_settings.cdn_zone_id = None

        _purge_cloudflare(["/blog"], mock_settings)

    def test_builds_full_urls_from_base(self) -> None:
        from app.workers.tasks.cms import _purge_cloudflare

        mock_settings = MagicMock()
        mock_settings.cdn_api_key = "test_key"
        mock_settings.cdn_zone_id = "zone123"
        mock_settings.cdn_base_url = "https://blog.stratum.ai"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            _purge_cloudflare(["/blog", "/sitemap.xml"], mock_settings)

            call_kwargs = mock_client.post.call_args
            files = call_kwargs.kwargs.get("json", {}).get("files", [])
            assert "https://blog.stratum.ai/blog" in files
            assert "https://blog.stratum.ai/sitemap.xml" in files


@pytest.mark.unit
class TestCloudfront:

    def test_skips_without_zone_id(self) -> None:
        from app.workers.tasks.cms import _purge_cloudfront

        mock_settings = MagicMock()
        mock_settings.cdn_zone_id = None

        _purge_cloudfront(["/blog"], mock_settings)

    def test_calls_boto3_create_invalidation(self) -> None:
        from app.workers.tasks.cms import _purge_cloudfront

        mock_settings = MagicMock()
        mock_settings.cdn_zone_id = "E1234567890"

        mock_cf_client = MagicMock()
        with patch("boto3.client", return_value=mock_cf_client):
            _purge_cloudfront(["/blog", "/sitemap.xml"], mock_settings)

            mock_cf_client.create_invalidation.assert_called_once()
            call_kwargs = mock_cf_client.create_invalidation.call_args.kwargs
            assert call_kwargs["DistributionId"] == "E1234567890"
            batch = call_kwargs["InvalidationBatch"]
            assert batch["Paths"]["Quantity"] == 2


@pytest.mark.unit
class TestFastly:

    def test_skips_without_api_key(self) -> None:
        from app.workers.tasks.cms import _purge_fastly

        mock_settings = MagicMock()
        mock_settings.cdn_api_key = None

        _purge_fastly(["/blog"], mock_settings)

    def test_skips_without_base_url(self) -> None:
        from app.workers.tasks.cms import _purge_fastly

        mock_settings = MagicMock()
        mock_settings.cdn_api_key = "key"
        mock_settings.cdn_base_url = ""

        _purge_fastly(["/blog"], mock_settings)

    def test_purges_each_path(self) -> None:
        from app.workers.tasks.cms import _purge_fastly

        mock_settings = MagicMock()
        mock_settings.cdn_api_key = "fastly_key"
        mock_settings.cdn_base_url = "https://cdn.stratum.ai"

        mock_resp = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            _purge_fastly(["/blog", "/sitemap.xml"], mock_settings)

            assert mock_client.request.call_count == 2
            first_call = mock_client.request.call_args_list[0]
            assert first_call.args[0] == "PURGE"
            assert first_call.args[1] == "https://cdn.stratum.ai/blog"
