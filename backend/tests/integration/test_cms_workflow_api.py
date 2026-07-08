# =============================================================================
# Stratum AI - CMS Workflow API Integration Tests
# =============================================================================
"""Integration tests for the CMS 2026 workflow endpoints.

Covers the post state machine (submit-for-review, approve, reject,
request-changes, schedule, publish, unpublish, archive), the workflow audit
history, and content versioning (versions list + restore) against the real
ASGI app and Postgres.
"""

from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


@pytest_asyncio.fixture
async def cms_client(client, test_user, test_tenant) -> AsyncClient:
    """An authenticated client whose JWT carries a CMS super_admin role."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=test_user["id"],
        additional_claims={
            "email": test_user["email"],
            "tenant_id": test_tenant["id"],
            "role": test_user["role"],
            "cms_role": "super_admin",
        },
    )
    client.headers["Authorization"] = f"Bearer {token}"
    client.headers["X-Tenant-ID"] = str(test_tenant["id"])
    return client


async def _create_post(client: AsyncClient, title="Workflow post", **extra) -> dict:
    body = {"title": title, "content": "<p>Workflow body.</p>", "status": "draft"}
    body.update(extra)
    resp = await client.post("/api/v1/cms/admin/posts", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _submit(client: AsyncClient, post_id: str, **params):
    return await client.post(
        f"/api/v1/cms/admin/posts/{post_id}/submit-for-review", params=params
    )


async def _in_review_post(client: AsyncClient, **extra) -> dict:
    post = await _create_post(client, **extra)
    resp = await _submit(client, post["id"])
    assert resp.status_code == 200, resp.text
    return post


# =============================================================================
# Submit for review
# =============================================================================
class TestSubmitForReview:
    @pytest.mark.asyncio
    async def test_submit_happy_path(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await _submit(cms_client, post["id"])
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "in_review"
        assert data["submitted_at"] is not None
        assert data["assigned_reviewer_id"] is None

    @pytest.mark.asyncio
    async def test_submit_with_reviewer(self, cms_client: AsyncClient, test_user):
        post = await _create_post(cms_client)
        resp = await _submit(cms_client, post["id"], reviewer_id=test_user["id"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["assigned_reviewer_id"] == test_user["id"]

    @pytest.mark.asyncio
    async def test_submit_from_published_rejected(self, cms_client: AsyncClient):
        post = await _create_post(cms_client, status="published")
        resp = await _submit(cms_client, post["id"])
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_not_found(self, cms_client: AsyncClient):
        resp = await _submit(cms_client, _MISSING)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"/api/v1/cms/admin/posts/{_MISSING}/submit-for-review"
        )
        assert resp.status_code == 403


# =============================================================================
# Approve / Reject / Request changes
# =============================================================================
class TestReviewDecisions:
    @pytest.mark.asyncio
    async def test_approve_happy_path(self, cms_client: AsyncClient, test_user):
        post = await _in_review_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/approve",
            params={"notes": "Looks good to me"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "approved"
        assert data["approved_at"] is not None
        assert data["approved_by_id"] == test_user["id"]

    @pytest.mark.asyncio
    async def test_approve_from_draft_rejected(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/approve")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{_MISSING}/approve")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_happy_path(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/reject",
            params={"reason": "Not aligned with the editorial calendar"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "rejected"
        assert data["rejection_reason"].startswith("Not aligned")

    @pytest.mark.asyncio
    async def test_reject_short_reason_validation(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/reject", params={"reason": "meh"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_wrong_status(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/reject",
            params={"reason": "Long enough rejection reason"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_request_changes_then_resubmit(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/request-changes",
            params={"notes": "Please tighten the introduction section"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "changes_requested"
        assert "tighten" in data["review_notes"]

        # CHANGES_REQUESTED is a valid submit-for-review source state
        resubmit = await _submit(cms_client, post["id"])
        assert resubmit.status_code == 200
        assert resubmit.json()["data"]["status"] == "in_review"

    @pytest.mark.asyncio
    async def test_request_changes_wrong_status(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/request-changes",
            params={"notes": "Long enough change request notes"},
        )
        assert resp.status_code == 400


# =============================================================================
# Schedule / Publish / Unpublish / Archive
# =============================================================================
class TestPublishLifecycle:
    @pytest.mark.asyncio
    async def test_schedule_from_draft_naive_datetime(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        # Naive datetime exercises the tzinfo backfill branch
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/schedule",
            params={"scheduled_at": "2030-01-01T09:00:00"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "scheduled"
        assert data["scheduled_at"].startswith("2030-01-01")

    @pytest.mark.asyncio
    async def test_schedule_in_past_rejected(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/schedule",
            params={"scheduled_at": "2020-01-01T00:00:00Z"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_schedule_wrong_status(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/schedule",
            params={"scheduled_at": "2030-01-01T09:00:00Z"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_schedule_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{_MISSING}/schedule",
            params={"scheduled_at": "2030-01-01T09:00:00Z"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_from_approved(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        approve = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/approve")
        assert approve.status_code == 200

        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/publish")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "published"
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_publish_wrong_status(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/publish")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_publish_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{_MISSING}/publish")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unpublish_from_published(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        publish = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/publish")
        assert publish.status_code == 200  # quick workflow: draft -> published

        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/unpublish")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "unpublished"

    @pytest.mark.asyncio
    async def test_unpublish_wrong_status(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/unpublish")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_archive_from_any_status(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/archive")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "archived"

    @pytest.mark.asyncio
    async def test_archive_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.post(f"/api/v1/cms/admin/posts/{_MISSING}/archive")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_lifecycle_requires_permission(
        self, authenticated_client: AsyncClient
    ):
        for action in ("approve", "publish", "unpublish", "archive"):
            resp = await authenticated_client.post(
                f"/api/v1/cms/admin/posts/{_MISSING}/{action}"
            )
            assert resp.status_code == 403, action


# =============================================================================
# Workflow history
# =============================================================================
class TestWorkflowHistory:
    @pytest.mark.asyncio
    async def test_history_records_transitions(self, cms_client: AsyncClient):
        post = await _in_review_post(cms_client)
        await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/approve")
        await cms_client.post(f"/api/v1/cms/admin/posts/{post['id']}/publish")

        resp = await cms_client.get(
            f"/api/v1/cms/admin/posts/{post['id']}/workflow-history"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 3
        actions = [h["action"] for h in data["history"]]
        assert set(actions) == {"submitted_for_review", "approved", "published"}
        published_entry = next(h for h in data["history"] if h["action"] == "published")
        assert published_entry["from_status"] == "approved"
        assert published_entry["to_status"] == "published"

        paged = await cms_client.get(
            f"/api/v1/cms/admin/posts/{post['id']}/workflow-history",
            params={"page": 1, "page_size": 2},
        )
        assert paged.json()["data"]["total"] == 3
        assert len(paged.json()["data"]["history"]) == 2

    @pytest.mark.asyncio
    async def test_history_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.get(
            f"/api/v1/cms/admin/posts/{_MISSING}/workflow-history"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_history_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"/api/v1/cms/admin/posts/{_MISSING}/workflow-history"
        )
        assert resp.status_code == 403


# =============================================================================
# Versions + restore
# =============================================================================
class TestPostVersions:
    async def _add_version(self, db_session, post_id: str, version: int = 1) -> None:
        from app.models.cms import CMSPostVersion

        db_session.add(
            CMSPostVersion(
                post_id=UUID(post_id),
                version=version,
                title="Original Title",
                slug="original-title-slug",
                excerpt="Original excerpt",
                content="<p>Original body.</p>",
                meta_title="Original meta",
                word_count=2,
                reading_time_minutes=1,
                change_summary="Initial snapshot",
            )
        )
        await db_session.flush()

    @pytest.mark.asyncio
    async def test_versions_empty(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{post['id']}/versions")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["versions"] == []
        assert data["current_version"] == 1

    @pytest.mark.asyncio
    async def test_versions_listing(self, cms_client: AsyncClient, db_session):
        post = await _create_post(cms_client)
        await self._add_version(db_session, post["id"])

        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{post['id']}/versions")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["versions"][0]["title"] == "Original Title"
        assert data["versions"][0]["change_summary"] == "Initial snapshot"

    @pytest.mark.asyncio
    async def test_versions_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{_MISSING}/versions")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_version(self, cms_client: AsyncClient, db_session):
        post = await _create_post(cms_client, title="Current Title")
        await self._add_version(db_session, post["id"])

        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/restore-version/1"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["restored_from_version"] == 1
        assert data["new_version"] == 2

        detail = await cms_client.get(f"/api/v1/cms/admin/posts/{post['id']}")
        assert detail.json()["data"]["title"] == "Original Title"
        assert detail.json()["data"]["slug"] == "original-title-slug"

    @pytest.mark.asyncio
    async def test_restore_missing_version(self, cms_client: AsyncClient):
        post = await _create_post(cms_client)
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{post['id']}/restore-version/99"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_post_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            f"/api/v1/cms/admin/posts/{_MISSING}/restore-version/1"
        )
        assert resp.status_code == 404
