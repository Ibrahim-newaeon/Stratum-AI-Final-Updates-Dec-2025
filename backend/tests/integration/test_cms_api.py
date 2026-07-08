# =============================================================================
# Stratum AI - CMS Admin API Integration Tests
# =============================================================================
"""Integration tests for the CMS admin API.

Exercises the real ASGI app against Postgres + Redis: public content
endpoints, admin post/category CRUD (including filters and 404/403 paths),
and the CMS role-permission gate edge cases. A ``cms_client`` fixture issues
a token carrying a ``cms_role`` claim so the ``check_cms_permission`` gate
passes; a plain admin (no ``cms_role``) is rejected with 403.

Workflow/versioning endpoints live in ``test_cms_workflow_api.py``; tags,
authors, pages, contacts, and CMS user management live in
``test_cms_admin_misc_api.py``.
"""

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


def _claims_client(client, test_user, test_tenant, **extra_claims) -> AsyncClient:
    """Re-sign the client token with custom claims (role / cms_role)."""
    from app.core.security import create_access_token

    claims = {
        "email": test_user["email"],
        "tenant_id": test_tenant["id"],
        "role": test_user["role"],
    }
    claims.update(extra_claims)
    token = create_access_token(subject=test_user["id"], additional_claims=claims)
    client.headers["Authorization"] = f"Bearer {token}"
    client.headers["X-Tenant-ID"] = str(test_tenant["id"])
    return client


def _post(title="Launch announcement", **extra):
    body = {"title": title, "content": "<p>Big news.</p>", "status": "draft"}
    body.update(extra)
    return body


async def _create_post(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/cms/admin/posts", json=_post(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _create_category(client: AsyncClient, name="News", **extra) -> dict:
    body = {"name": name}
    body.update(extra)
    resp = await client.post("/api/v1/cms/admin/categories", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _create_tag(client: AsyncClient, name="ai", **extra) -> dict:
    body = {"name": name}
    body.update(extra)
    resp = await client.post("/api/v1/cms/admin/tags", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _create_author(client: AsyncClient, name="Jane Author", **extra) -> dict:
    body = {"name": name}
    body.update(extra)
    resp = await client.post("/api/v1/cms/admin/authors", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _set_tags(client: AsyncClient, post_id: str, tag_ids: list) -> dict:
    """Attach tags via PATCH.

    NOTE: creating a post with ``tag_ids`` is intentionally avoided here —
    ``admin_create_post`` 500s (sqlalchemy MissingGreenlet) whenever
    ``tag_ids`` is non-empty (see cms.py:875, reported as a bug). The update
    endpoint eager-loads the tags collection, so it works.
    """
    resp = await client.patch(
        f"/api/v1/cms/admin/posts/{post_id}", json={"tag_ids": tag_ids}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# =============================================================================
# Posts
# =============================================================================
class TestAdminPosts:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/cms/admin/posts", json=_post())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_requires_cms_permission(self, authenticated_client: AsyncClient):
        # Plain ADMIN without a cms_role claim is rejected by the CMS gate.
        resp = await authenticated_client.post("/api/v1/cms/admin/posts", json=_post())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_post(self, cms_client: AsyncClient):
        data = await _create_post(cms_client, title="Hello CMS")
        assert data["title"] == "Hello CMS"
        assert data["slug"]

    @pytest.mark.asyncio
    async def test_create_generates_unique_slug(self, cms_client: AsyncClient):
        a = await _create_post(cms_client, title="Same Title")
        b = await _create_post(cms_client, title="Same Title")
        assert a["slug"] != b["slug"]

    @pytest.mark.asyncio
    async def test_list_posts(self, cms_client: AsyncClient):
        await _create_post(cms_client, title="Listed Post")
        resp = await cms_client.get("/api/v1/cms/admin/posts")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, cms_client: AsyncClient):
        created = await _create_post(cms_client, title="Detail Post")
        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Detail Post"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.get(f"/api/v1/cms/admin/posts/{_MISSING}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_post(self, cms_client: AsyncClient):
        created = await _create_post(cms_client, title="Doomed Post")
        resp = await cms_client.delete(f"/api/v1/cms/admin/posts/{created['id']}")
        assert resp.status_code in {200, 204}


# =============================================================================
# Categories
# =============================================================================
class TestAdminCategories:
    @pytest.mark.asyncio
    async def test_create_category(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/categories", json={"name": "Product Updates"}
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Product Updates"

    @pytest.mark.asyncio
    async def test_create_category_invalid_color(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/categories",
            json={"name": "Bad Color", "color": "notahex"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_categories(self, cms_client: AsyncClient):
        await cms_client.post(
            "/api/v1/cms/admin/categories", json={"name": "Listed Cat"}
        )
        resp = await cms_client.get("/api/v1/cms/admin/categories")
        assert resp.status_code == 200


# =============================================================================
# Permission gate edge cases
# =============================================================================
class TestCmsPermissionGate:
    @pytest.mark.asyncio
    async def test_platform_superadmin_without_cms_role_allowed(
        self, client: AsyncClient, test_user, test_tenant
    ):
        # Fallback path: platform superadmin passes even without a cms_role.
        sa = _claims_client(client, test_user, test_tenant, role="superadmin")
        resp = await sa.get("/api/v1/cms/admin/posts")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_cms_role_claim_rejected(
        self, client: AsyncClient, test_user, test_tenant
    ):
        bogus = _claims_client(client, test_user, test_tenant, cms_role="bogus_role")
        resp = await bogus.get("/api/v1/cms/admin/posts")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_role_can_view_but_not_create(
        self, client: AsyncClient, test_user, test_tenant
    ):
        viewer = _claims_client(client, test_user, test_tenant, cms_role="viewer")
        list_resp = await viewer.get("/api/v1/cms/admin/posts")
        assert list_resp.status_code == 200
        create_resp = await viewer.post("/api/v1/cms/admin/posts", json=_post())
        assert create_resp.status_code == 403


# =============================================================================
# Public endpoints
# =============================================================================
class TestPublicPosts:
    @pytest_asyncio.fixture
    async def published_post(self, cms_client: AsyncClient) -> dict:
        """A published post wired to a category, an author, and a tag."""
        category = await _create_category(cms_client, name="Product News")
        author = await _create_author(cms_client, name="Jane Author")
        tag = await _create_tag(cms_client, name="launch")
        post = await _create_post(
            cms_client,
            title="Public launch guide",
            status="published",
            content_type="guide",
            is_featured=True,
            category_id=category["id"],
            author_id=author["id"],
        )
        # Tags attached via PATCH — create-with-tags 500s (known bug, cms.py:875)
        post = await _set_tags(cms_client, post["id"], [tag["id"]])
        return {"post": post, "category": category, "author": author, "tag": tag}

    @pytest.mark.asyncio
    async def test_list_public_posts_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/cms/posts")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["posts"] == []

    @pytest.mark.asyncio
    async def test_list_public_posts_published_only_with_relations(
        self, cms_client: AsyncClient, published_post
    ):
        await _create_post(cms_client, title="Hidden draft", status="draft")

        resp = await cms_client.get("/api/v1/cms/posts")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        post = data["posts"][0]
        assert post["title"] == "Public launch guide"
        assert post["category"]["name"] == "Product News"
        assert post["author"]["name"] == "Jane Author"
        assert [t["name"] for t in post["tags"]] == ["launch"]

    @pytest.mark.asyncio
    async def test_list_public_posts_filters(
        self, cms_client: AsyncClient, published_post
    ):
        cat_slug = published_post["category"]["slug"]
        tag_slug = published_post["tag"]["slug"]

        by_category = await cms_client.get(
            "/api/v1/cms/posts", params={"category_slug": cat_slug}
        )
        assert by_category.json()["data"]["total"] == 1

        # Unknown category slug is ignored (filter skipped), not a 404
        unknown_cat = await cms_client.get(
            "/api/v1/cms/posts", params={"category_slug": "does-not-exist"}
        )
        assert unknown_cat.status_code == 200
        assert unknown_cat.json()["data"]["total"] == 1

        by_tag = await cms_client.get(
            "/api/v1/cms/posts", params={"tag_slug": tag_slug}
        )
        assert by_tag.json()["data"]["total"] == 1

        by_type = await cms_client.get(
            "/api/v1/cms/posts", params={"content_type": "guide"}
        )
        assert by_type.json()["data"]["total"] == 1
        wrong_type = await cms_client.get(
            "/api/v1/cms/posts", params={"content_type": "case_study"}
        )
        assert wrong_type.json()["data"]["total"] == 0

        by_search = await cms_client.get(
            "/api/v1/cms/posts", params={"search": "launch guide"}
        )
        assert by_search.json()["data"]["total"] == 1
        no_match = await cms_client.get(
            "/api/v1/cms/posts", params={"search": "zzz-no-such-term"}
        )
        assert no_match.json()["data"]["total"] == 0

        featured = await cms_client.get(
            "/api/v1/cms/posts", params={"featured_only": "true"}
        )
        assert featured.json()["data"]["total"] == 1

    @pytest.mark.asyncio
    async def test_list_public_posts_pagination(self, cms_client: AsyncClient):
        await _create_post(cms_client, title="First public", status="published")
        await _create_post(cms_client, title="Second public", status="published")

        resp = await cms_client.get(
            "/api/v1/cms/posts", params={"page": 2, "page_size": 1}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert len(data["posts"]) == 1
        assert data["page"] == 2
        assert data["page_size"] == 1

    @pytest.mark.asyncio
    async def test_get_post_by_slug_increments_view_count(
        self, cms_client: AsyncClient, published_post
    ):
        slug = published_post["post"]["slug"]

        first = await cms_client.get(f"/api/v1/cms/posts/{slug}")
        assert first.status_code == 200
        assert first.json()["data"]["view_count"] == 1
        assert first.json()["data"]["category"]["name"] == "Product News"

        second = await cms_client.get(f"/api/v1/cms/posts/{slug}")
        assert second.json()["data"]["view_count"] == 2

    @pytest.mark.asyncio
    async def test_get_post_by_slug_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/cms/posts/no-such-slug")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_draft_post_by_slug_not_visible(self, cms_client: AsyncClient):
        draft = await _create_post(cms_client, title="Sneaky draft", status="draft")
        resp = await cms_client.get(f"/api/v1/cms/posts/{draft['slug']}")
        assert resp.status_code == 404


class TestPublicCategoriesTagsContact:
    @pytest.mark.asyncio
    async def test_public_categories_active_only_toggle(self, cms_client: AsyncClient):
        await _create_category(cms_client, name="Active Cat", is_active=True)
        await _create_category(cms_client, name="Inactive Cat", is_active=False)

        default = await cms_client.get("/api/v1/cms/categories")
        assert default.status_code == 200
        names = [c["name"] for c in default.json()["data"]["categories"]]
        assert "Active Cat" in names
        assert "Inactive Cat" not in names

        include_all = await cms_client.get(
            "/api/v1/cms/categories", params={"active_only": "false"}
        )
        all_names = [c["name"] for c in include_all.json()["data"]["categories"]]
        assert "Inactive Cat" in all_names

    @pytest.mark.asyncio
    async def test_public_tags(self, cms_client: AsyncClient):
        await _create_tag(cms_client, name="public-tag")
        resp = await cms_client.get("/api/v1/cms/tags")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert "public-tag" in [t["name"] for t in data["tags"]]

    @pytest.mark.asyncio
    async def test_contact_form_submit(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/cms/contact",
            json={
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "company": "Analytical Engines",
                "message": "I would like a demo of the trust engine please.",
                "source_page": "/pricing",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["data"]["submitted"] is True
        assert "Thank you" in body["message"]

    @pytest.mark.asyncio
    async def test_contact_form_validation_error(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/cms/contact",
            json={"name": "No Message", "email": "nomsg@example.com"},
        )
        assert resp.status_code == 422


class TestPublicPages:
    @pytest.mark.asyncio
    async def test_get_published_page(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/pages",
            json={
                "title": "About Us",
                "content": "<p>We gate automation on trust.</p>",
                "status": "published",
            },
        )
        assert create.status_code == 201
        slug = create.json()["data"]["slug"]

        resp = await cms_client.get(f"/api/v1/cms/pages/{slug}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "About Us"
        assert data["template"] == "default"
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_get_draft_page_not_visible(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/pages",
            json={"title": "Secret Draft Page", "status": "draft"},
        )
        assert create.status_code == 201
        slug = create.json()["data"]["slug"]

        resp = await cms_client.get(f"/api/v1/cms/pages/{slug}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_page_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/cms/pages/no-such-page")
        assert resp.status_code == 404


# =============================================================================
# Admin posts — filters, detail, update, delete
# =============================================================================
class TestAdminPostsListFilters:
    @pytest.mark.asyncio
    async def test_list_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/posts")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_filters(self, cms_client: AsyncClient):
        await _create_post(cms_client, title="Draft alpha", status="draft")
        await _create_post(
            cms_client,
            title="Published beta",
            status="published",
            content_type="case_study",
        )

        by_status = await cms_client.get(
            "/api/v1/cms/admin/posts", params={"status_filter": "draft"}
        )
        assert by_status.status_code == 200
        assert by_status.json()["data"]["total"] == 1
        assert by_status.json()["data"]["posts"][0]["title"] == "Draft alpha"

        by_type = await cms_client.get(
            "/api/v1/cms/admin/posts", params={"content_type": "case_study"}
        )
        assert by_type.json()["data"]["total"] == 1

        by_search = await cms_client.get(
            "/api/v1/cms/admin/posts", params={"search": "beta"}
        )
        assert by_search.json()["data"]["total"] == 1

        paged = await cms_client.get(
            "/api/v1/cms/admin/posts", params={"page": 2, "page_size": 1}
        )
        assert paged.json()["data"]["total"] == 2
        assert len(paged.json()["data"]["posts"]) == 1

    @pytest.mark.asyncio
    async def test_get_detail_requires_permission(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(f"/api/v1/cms/admin/posts/{_MISSING}")
        assert resp.status_code == 403


class TestAdminPostCreateEdgeCases:
    @pytest.mark.asyncio
    async def test_create_without_content_has_no_reading_time(
        self, cms_client: AsyncClient
    ):
        resp = await cms_client.post(
            "/api/v1/cms/admin/posts",
            json={"title": "Contentless", "status": "draft"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["reading_time_minutes"] is None
        assert data["word_count"] is None

    @pytest.mark.asyncio
    async def test_attach_tags_via_update_increments_usage(
        self, cms_client: AsyncClient
    ):
        tag_a = await _create_tag(cms_client, name="tag-a")
        tag_b = await _create_tag(cms_client, name="tag-b")

        post = await _create_post(cms_client, title="Tagged post")
        data = await _set_tags(cms_client, post["id"], [tag_a["id"], tag_b["id"]])
        assert sorted(t["name"] for t in data["tags"]) == ["tag-a", "tag-b"]

        tags = await cms_client.get("/api/v1/cms/admin/tags")
        counts = {t["name"]: t["usage_count"] for t in tags.json()["data"]["tags"]}
        assert counts["tag-a"] == 1
        assert counts["tag-b"] == 1

    @pytest.mark.asyncio
    async def test_create_invalid_status_rejected(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/posts",
            json={"title": "Bad status", "status": "nonsense"},
        )
        assert resp.status_code == 422


class TestAdminPostUpdate:
    @pytest.mark.asyncio
    async def test_update_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/cms/admin/posts/{_MISSING}", json={"title": "Nope"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/posts/{_MISSING}", json={"title": "Ghost"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_all_fields(self, cms_client: AsyncClient):
        category = await _create_category(cms_client, name="Update Cat")
        author = await _create_author(cms_client, name="Update Author")
        tag_old = await _create_tag(cms_client, name="old-tag")
        tag_new = await _create_tag(cms_client, name="new-tag")
        post = await _create_post(cms_client, title="Before update")
        # Attach the old tag first so the update below exercises the
        # decrement-then-swap branch (create-with-tags 500s — known bug).
        await _set_tags(cms_client, post["id"], [tag_old["id"]])

        resp = await cms_client.patch(
            f"/api/v1/cms/admin/posts/{post['id']}",
            json={
                "title": "After update",
                "slug": "after-update-slug",
                "excerpt": "Updated excerpt",
                "content": "<p>" + "word " * 400 + "</p>",
                "content_json": {"blocks": [{"type": "paragraph"}]},
                "status": "published",
                "content_type": "case_study",
                "category_id": category["id"],
                "author_id": author["id"],
                "scheduled_at": "2030-06-01T00:00:00Z",
                "meta_title": "Meta title",
                "meta_description": "Meta description",
                "canonical_url": "https://example.com/after-update",
                "og_image_url": "https://example.com/og.png",
                "featured_image_url": "https://example.com/hero.png",
                "featured_image_alt": "Hero image",
                "is_featured": True,
                "allow_comments": False,
                "tag_ids": [tag_new["id"]],
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["title"] == "After update"
        assert data["slug"] == "after-update-slug"
        assert data["status"] == "published"
        assert data["published_at"] is not None  # draft -> published stamps it
        assert data["content_type"] == "case_study"
        assert data["category"]["id"] == category["id"]
        assert data["author"]["id"] == author["id"]
        assert data["word_count"] >= 400
        assert data["reading_time_minutes"] == 2
        assert data["is_featured"] is True
        assert data["allow_comments"] is False
        assert [t["name"] for t in data["tags"]] == ["new-tag"]

        # Tag usage counts swapped: old decremented, new incremented
        tags = await cms_client.get("/api/v1/cms/admin/tags")
        counts = {t["name"]: t["usage_count"] for t in tags.json()["data"]["tags"]}
        assert counts["old-tag"] == 0
        assert counts["new-tag"] == 1

    @pytest.mark.asyncio
    async def test_update_reading_time_override(self, cms_client: AsyncClient):
        post = await _create_post(cms_client, title="Reading override")
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/posts/{post['id']}",
            json={"reading_time_minutes": 42},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["reading_time_minutes"] == 42


class TestAdminPostDelete:
    @pytest.mark.asyncio
    async def test_delete_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/cms/admin/posts/{_MISSING}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.delete(f"/api/v1/cms/admin/posts/{_MISSING}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_deleted_post_disappears(self, cms_client: AsyncClient):
        post = await _create_post(cms_client, title="Soft deleted")
        resp = await cms_client.delete(f"/api/v1/cms/admin/posts/{post['id']}")
        assert resp.status_code == 204

        detail = await cms_client.get(f"/api/v1/cms/admin/posts/{post['id']}")
        assert detail.status_code == 404


# =============================================================================
# Admin categories — update / delete / permission paths
# =============================================================================
class TestAdminCategoriesMore:
    @pytest.mark.asyncio
    async def test_list_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/categories")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cms/admin/categories", json={"name": "Nope"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_category(self, cms_client: AsyncClient):
        category = await _create_category(cms_client, name="Old Name")
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/categories/{category['id']}",
            json={
                "name": "New Name",
                "slug": "new-name-slug",
                "description": "Updated description",
                "color": "#FF5A1F",
                "icon": "flame",
                "display_order": 5,
                "is_active": False,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["name"] == "New Name"
        assert data["slug"] == "new-name-slug"
        assert data["color"] == "#FF5A1F"
        assert data["display_order"] == 5
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_category_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/categories/{_MISSING}", json={"name": "Ghost"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/cms/admin/categories/{_MISSING}", json={"name": "Nope"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_category(self, cms_client: AsyncClient):
        category = await _create_category(cms_client, name="Doomed Cat")
        resp = await cms_client.delete(f"/api/v1/cms/admin/categories/{category['id']}")
        assert resp.status_code == 204

        listing = await cms_client.get("/api/v1/cms/admin/categories")
        names = [c["name"] for c in listing.json()["data"]["categories"]]
        assert "Doomed Cat" not in names

    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.delete(f"/api/v1/cms/admin/categories/{_MISSING}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            f"/api/v1/cms/admin/categories/{_MISSING}"
        )
        assert resp.status_code == 403
