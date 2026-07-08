# =============================================================================
# Stratum AI - CMS Admin Misc API Integration Tests
# =============================================================================
"""Integration tests for CMS admin tags, authors, pages, contact submissions,
and CMS user management (roles, invites, permissions) against the real ASGI
app and Postgres.
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


@pytest_asyncio.fixture
async def editor_user(db_session, test_tenant) -> dict:
    """A second user holding a CMS editor role (role change/revoke target)."""
    from app.base_models import User, UserRole
    from app.core.security import get_password_hash

    user = User(
        tenant_id=test_tenant["id"],
        email="editor@example.com",
        email_hash="editor@example.com",
        password_hash=get_password_hash("editorpassword123"),
        full_name="Editor User",
        role=UserRole.ANALYST,
        cms_role="editor",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": user.email}


@pytest_asyncio.fixture
async def plain_user(db_session, test_tenant) -> dict:
    """A user without any CMS role."""
    from app.base_models import User, UserRole
    from app.core.security import get_password_hash

    user = User(
        tenant_id=test_tenant["id"],
        email="plain@example.com",
        email_hash="plain@example.com",
        password_hash=get_password_hash("plainpassword123"),
        full_name="Plain User",
        role=UserRole.ANALYST,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"id": user.id, "email": user.email}


@pytest_asyncio.fixture
async def global_cms_tenant(db_session, test_tenant) -> None:
    """Ensure tenant id=1 exists (invite_cms_user hardcodes tenant_id=1)."""
    from sqlalchemy import select

    from app.base_models import Tenant

    existing = await db_session.execute(select(Tenant).where(Tenant.id == 1))
    if existing.scalar_one_or_none() is None:
        db_session.add(
            Tenant(
                id=1,
                name="Global CMS Tenant",
                slug="global-cms-tenant",
                plan="enterprise",
                max_users=100,
                max_campaigns=100,
            )
        )
        await db_session.flush()


async def _submit_contact(client: AsyncClient, email="lead@example.com") -> None:
    resp = await client.post(
        "/api/v1/cms/contact",
        json={
            "name": "Interested Lead",
            "email": email,
            "message": "Please send more information about pricing tiers.",
        },
    )
    assert resp.status_code == 201, resp.text


async def _first_contact_id(client: AsyncClient) -> str:
    resp = await client.get("/api/v1/cms/admin/contacts")
    assert resp.status_code == 200, resp.text
    contacts = resp.json()["data"]["contacts"]
    assert contacts, "expected at least one contact submission"
    return contacts[0]["id"]


# =============================================================================
# Tags
# =============================================================================
class TestAdminTags:
    @pytest.mark.asyncio
    async def test_list_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/tags")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_and_list(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/tags",
            json={"name": "Machine Learning", "color": "#06B6D4"},
        )
        assert create.status_code == 201, create.text
        data = create.json()["data"]
        assert data["slug"] == "machine-learning"  # auto-slugified
        assert data["color"] == "#06B6D4"
        assert data["usage_count"] == 0

        listing = await cms_client.get("/api/v1/cms/admin/tags")
        assert listing.status_code == 200
        assert "Machine Learning" in [t["name"] for t in listing.json()["data"]["tags"]]

    @pytest.mark.asyncio
    async def test_create_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cms/admin/tags", json={"name": "Nope"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_invalid_color(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/tags", json={"name": "Bad", "color": "red"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_tag(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/tags", json={"name": "Before"}
        )
        tag_id = create.json()["data"]["id"]

        resp = await cms_client.patch(
            f"/api/v1/cms/admin/tags/{tag_id}",
            json={
                "name": "After",
                "slug": "after-slug",
                "description": "Updated tag",
                "color": "#10B981",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["name"] == "After"
        assert data["slug"] == "after-slug"
        assert data["description"] == "Updated tag"
        assert data["color"] == "#10B981"

    @pytest.mark.asyncio
    async def test_update_tag_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/tags/{_MISSING}", json={"name": "Ghost"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_tag(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/tags", json={"name": "Doomed"}
        )
        tag_id = create.json()["data"]["id"]

        resp = await cms_client.delete(f"/api/v1/cms/admin/tags/{tag_id}")
        assert resp.status_code == 204

        listing = await cms_client.get("/api/v1/cms/admin/tags")
        assert "Doomed" not in [t["name"] for t in listing.json()["data"]["tags"]]

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.delete(f"/api/v1/cms/admin/tags/{_MISSING}")
        assert resp.status_code == 404


# =============================================================================
# Authors
# =============================================================================
class TestAdminAuthors:
    @pytest.mark.asyncio
    async def test_list_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/authors")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_full_and_list(self, cms_client: AsyncClient, test_user):
        create = await cms_client.post(
            "/api/v1/cms/admin/authors",
            json={
                "name": "Grace Hopper",
                "email": "grace@example.com",
                "bio": "Compiler pioneer",
                "avatar_url": "https://example.com/grace.png",
                "job_title": "Rear Admiral",
                "company": "US Navy",
                "twitter_handle": "gracehopper",
                "linkedin_url": "https://linkedin.com/in/grace",
                "github_handle": "ghopper",
                "website_url": "https://example.com",
                "user_id": test_user["id"],
            },
        )
        assert create.status_code == 201, create.text
        data = create.json()["data"]
        assert data["slug"] == "grace-hopper"
        assert data["user_id"] == test_user["id"]
        assert data["job_title"] == "Rear Admiral"

        listing = await cms_client.get("/api/v1/cms/admin/authors")
        assert listing.status_code == 200
        assert listing.json()["data"]["total"] == 1

    @pytest.mark.asyncio
    async def test_create_duplicate_slug_gets_suffix(self, cms_client: AsyncClient):
        first = await cms_client.post(
            "/api/v1/cms/admin/authors", json={"name": "Same Name"}
        )
        second = await cms_client.post(
            "/api/v1/cms/admin/authors", json={"name": "Same Name"}
        )
        third = await cms_client.post(
            "/api/v1/cms/admin/authors", json={"name": "Same Name"}
        )
        assert first.json()["data"]["slug"] == "same-name"
        assert second.json()["data"]["slug"] == "same-name-1"
        assert third.json()["data"]["slug"] == "same-name-2"

    @pytest.mark.asyncio
    async def test_update_author(self, cms_client: AsyncClient, test_user):
        create = await cms_client.post(
            "/api/v1/cms/admin/authors", json={"name": "Old Author"}
        )
        author_id = create.json()["data"]["id"]

        resp = await cms_client.patch(
            f"/api/v1/cms/admin/authors/{author_id}",
            json={
                "name": "New Author",
                "slug": "new-author-slug",
                "email": "new@example.com",
                "bio": "Updated bio",
                "avatar_url": "https://example.com/new.png",
                "job_title": "Editor",
                "company": "Stratum",
                "twitter_handle": "newauthor",
                "linkedin_url": "https://linkedin.com/in/new",
                "github_handle": "newauthor",
                "website_url": "https://new.example.com",
                "user_id": test_user["id"],
                "is_active": False,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["name"] == "New Author"
        assert data["slug"] == "new-author-slug"
        assert data["email"] == "new@example.com"
        assert data["is_active"] is False
        assert data["user_id"] == test_user["id"]

    @pytest.mark.asyncio
    async def test_update_author_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/authors/{_MISSING}", json={"name": "Ghost"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_author(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/authors", json={"name": "Doomed Author"}
        )
        author_id = create.json()["data"]["id"]

        resp = await cms_client.delete(f"/api/v1/cms/admin/authors/{author_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_author_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.delete(f"/api/v1/cms/admin/authors/{_MISSING}")
        assert resp.status_code == 404


# =============================================================================
# Pages
# =============================================================================
class TestAdminPages:
    @pytest.mark.asyncio
    async def test_list_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/pages")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_draft_page(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/pages",
            json={"title": "Draft Page", "content": "<p>WIP</p>"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["status"] == "draft"
        assert data["published_at"] is None
        assert data["slug"] == "draft-page"

    @pytest.mark.asyncio
    async def test_create_published_page_stamps_published_at(
        self, cms_client: AsyncClient
    ):
        resp = await cms_client.post(
            "/api/v1/cms/admin/pages",
            json={
                "title": "Live Page",
                "status": "published",
                "show_in_navigation": True,
                "navigation_label": "Live",
                "navigation_order": 3,
                "template": "landing",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["published_at"] is not None
        assert data["show_in_navigation"] is True
        assert data["navigation_label"] == "Live"
        assert data["template"] == "landing"

    @pytest.mark.asyncio
    async def test_create_invalid_status(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/pages",
            json={"title": "Bad", "status": "in_orbit"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_pages(self, cms_client: AsyncClient):
        await cms_client.post("/api/v1/cms/admin/pages", json={"title": "Page One"})
        await cms_client.post("/api/v1/cms/admin/pages", json={"title": "Page Two"})
        resp = await cms_client.get("/api/v1/cms/admin/pages")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_update_page_and_publish(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/pages", json={"title": "Editable Page"}
        )
        page_id = create.json()["data"]["id"]

        resp = await cms_client.patch(
            f"/api/v1/cms/admin/pages/{page_id}",
            json={
                "title": "Edited Page",
                "slug": "edited-page-slug",
                "content": "<p>Edited</p>",
                "content_json": {"blocks": []},
                "status": "published",
                "meta_title": "Edited meta",
                "meta_description": "Edited description",
                "show_in_navigation": True,
                "navigation_label": "Edited",
                "navigation_order": 7,
                "template": "landing",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["title"] == "Edited Page"
        assert data["status"] == "published"
        assert data["published_at"] is not None  # draft -> published stamps it
        assert data["navigation_order"] == 7

    @pytest.mark.asyncio
    async def test_update_page_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/pages/{_MISSING}", json={"title": "Ghost"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_page(self, cms_client: AsyncClient):
        create = await cms_client.post(
            "/api/v1/cms/admin/pages", json={"title": "Doomed Page"}
        )
        page_id = create.json()["data"]["id"]

        resp = await cms_client.delete(f"/api/v1/cms/admin/pages/{page_id}")
        assert resp.status_code == 204

        listing = await cms_client.get("/api/v1/cms/admin/pages")
        titles = [p["title"] for p in listing.json()["data"]["pages"]]
        assert "Doomed Page" not in titles

    @pytest.mark.asyncio
    async def test_delete_page_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.delete(f"/api/v1/cms/admin/pages/{_MISSING}")
        assert resp.status_code == 404


# =============================================================================
# Contact submissions
# =============================================================================
class TestAdminContacts:
    @pytest.mark.asyncio
    async def test_list_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/contacts")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_contacts(self, cms_client: AsyncClient):
        await _submit_contact(cms_client, email="one@example.com")
        await _submit_contact(cms_client, email="two@example.com")

        resp = await cms_client.get("/api/v1/cms/admin/contacts")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 2
        emails = {c["email"] for c in data["contacts"]}
        assert emails == {"one@example.com", "two@example.com"}

        paged = await cms_client.get(
            "/api/v1/cms/admin/contacts", params={"page": 2, "page_size": 1}
        )
        assert paged.json()["data"]["total"] == 2
        assert len(paged.json()["data"]["contacts"]) == 1

    @pytest.mark.asyncio
    async def test_mark_read_and_unread(self, cms_client: AsyncClient):
        await _submit_contact(cms_client)
        contact_id = await _first_contact_id(cms_client)

        read = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{contact_id}/read", json={"is_read": True}
        )
        assert read.status_code == 200, read.text
        assert read.json()["data"]["is_read"] is True
        assert read.json()["data"]["read_at"] is not None

        # unread_only filter no longer returns it
        unread = await cms_client.get(
            "/api/v1/cms/admin/contacts", params={"unread_only": "true"}
        )
        assert unread.json()["data"]["total"] == 0

        # Toggle back clears read_at
        unread_again = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{contact_id}/read", json={"is_read": False}
        )
        assert unread_again.json()["data"]["is_read"] is False
        assert unread_again.json()["data"]["read_at"] is None

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{_MISSING}/read", json={"is_read": True}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_responded(self, cms_client: AsyncClient):
        await _submit_contact(cms_client)
        contact_id = await _first_contact_id(cms_client)

        resp = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{contact_id}/responded",
            json={"is_responded": True, "response_notes": "Sent pricing deck"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["is_responded"] is True
        assert data["responded_at"] is not None
        assert data["response_notes"] == "Sent pricing deck"

        cleared = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{contact_id}/responded",
            json={"is_responded": False},
        )
        assert cleared.json()["data"]["is_responded"] is False
        assert cleared.json()["data"]["responded_at"] is None

    @pytest.mark.asyncio
    async def test_mark_responded_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{_MISSING}/responded",
            json={"is_responded": True},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_spam_excludes_from_default_list(self, cms_client: AsyncClient):
        await _submit_contact(cms_client)
        contact_id = await _first_contact_id(cms_client)

        resp = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{contact_id}/spam", json={"is_spam": True}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_spam"] is True

        default = await cms_client.get("/api/v1/cms/admin/contacts")
        assert default.json()["data"]["total"] == 0

        include_spam = await cms_client.get(
            "/api/v1/cms/admin/contacts", params={"exclude_spam": "false"}
        )
        assert include_spam.json()["data"]["total"] == 1

    @pytest.mark.asyncio
    async def test_mark_spam_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/contacts/{_MISSING}/spam", json={"is_spam": True}
        )
        assert resp.status_code == 404


# =============================================================================
# CMS user management
# =============================================================================
class TestCmsUserManagement:
    @pytest.mark.asyncio
    async def test_list_users_requires_permission(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get("/api/v1/cms/admin/users")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_users(self, cms_client: AsyncClient, editor_user):
        resp = await cms_client.get("/api/v1/cms/admin/users")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] >= 1
        by_id = {u["id"]: u for u in data["users"]}
        assert editor_user["id"] in by_id
        assert by_id[editor_user["id"]]["cms_role"] == "editor"

    @pytest.mark.asyncio
    async def test_my_permissions(self, cms_client: AsyncClient):
        resp = await cms_client.get("/api/v1/cms/admin/me/permissions")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["role"] == "super_admin"
        assert data["permissions"]["create_post"] is True
        assert data["permissions"]["manage_users"] is True

    @pytest.mark.asyncio
    async def test_my_permissions_without_role(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cms/admin/me/permissions")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_my_permissions_invalid_role(
        self, client: AsyncClient, test_user, test_tenant
    ):
        from app.core.security import create_access_token

        token = create_access_token(
            subject=test_user["id"],
            additional_claims={
                "email": test_user["email"],
                "tenant_id": test_tenant["id"],
                "role": test_user["role"],
                "cms_role": "not_a_role",
            },
        )
        client.headers["Authorization"] = f"Bearer {token}"
        client.headers["X-Tenant-ID"] = str(test_tenant["id"])
        resp = await client.get("/api/v1/cms/admin/me/permissions")
        assert resp.status_code == 403
        assert "Invalid CMS role" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_assign_role(self, cms_client: AsyncClient, plain_user):
        resp = await cms_client.post(
            "/api/v1/cms/admin/users/assign",
            json={"user_id": plain_user["id"], "cms_role": "author"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["id"] == plain_user["id"]
        assert data["cms_role"] == "author"

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/users/assign",
            json={"user_id": 99999999, "cms_role": "author"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_assign_invalid_role(self, cms_client: AsyncClient, plain_user):
        resp = await cms_client.post(
            "/api/v1/cms/admin/users/assign",
            json={"user_id": plain_user["id"], "cms_role": "galactic_overlord"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_assign_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cms/admin/users/assign",
            json={"user_id": 1, "cms_role": "author"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_role(self, cms_client: AsyncClient, editor_user):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/users/{editor_user['id']}/role",
            json={"cms_role": "author"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["cms_role"] == "author"

    @pytest.mark.asyncio
    async def test_update_own_role_rejected(self, cms_client: AsyncClient, test_user):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/users/{test_user['id']}/role",
            json={"cms_role": "author"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_role_user_without_cms_role(
        self, cms_client: AsyncClient, plain_user
    ):
        resp = await cms_client.patch(
            f"/api/v1/cms/admin/users/{plain_user['id']}/role",
            json={"cms_role": "author"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_role_user_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.patch(
            "/api/v1/cms/admin/users/99999999/role", json={"cms_role": "author"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_role(self, cms_client: AsyncClient, editor_user):
        resp = await cms_client.delete(
            f"/api/v1/cms/admin/users/{editor_user['id']}/role"
        )
        assert resp.status_code == 200, resp.text

        listing = await cms_client.get("/api/v1/cms/admin/users")
        ids = [u["id"] for u in listing.json()["data"]["users"]]
        assert editor_user["id"] not in ids

    @pytest.mark.asyncio
    async def test_revoke_own_role_rejected(self, cms_client: AsyncClient, test_user):
        resp = await cms_client.delete(
            f"/api/v1/cms/admin/users/{test_user['id']}/role"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_revoke_role_user_not_found(self, cms_client: AsyncClient):
        resp = await cms_client.delete("/api/v1/cms/admin/users/99999999/role")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invite_user(self, cms_client: AsyncClient, global_cms_tenant):
        resp = await cms_client.post(
            "/api/v1/cms/admin/users/invite",
            json={
                "email": "invited@example.com",
                "full_name": "Invited Writer",
                "password": "supersecurepw123",
                "cms_role": "contributor",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["email"] == "invited@example.com"
        assert data["cms_role"] == "contributor"

        listing = await cms_client.get("/api/v1/cms/admin/users")
        ids = [u["id"] for u in listing.json()["data"]["users"]]
        assert data["id"] in ids

    @pytest.mark.asyncio
    async def test_invite_duplicate_email(
        self, cms_client: AsyncClient, global_cms_tenant
    ):
        body = {
            "email": "twice@example.com",
            "full_name": "Twice Invited",
            "password": "supersecurepw123",
            "cms_role": "viewer",
        }
        first = await cms_client.post("/api/v1/cms/admin/users/invite", json=body)
        assert first.status_code == 200, first.text

        second = await cms_client.post("/api/v1/cms/admin/users/invite", json=body)
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_invite_invalid_role(self, cms_client: AsyncClient):
        resp = await cms_client.post(
            "/api/v1/cms/admin/users/invite",
            json={
                "email": "badrole@example.com",
                "full_name": "Bad Role",
                "password": "supersecurepw123",
                "cms_role": "wizard",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invite_requires_permission(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cms/admin/users/invite",
            json={
                "email": "noperm@example.com",
                "full_name": "No Perm",
                "password": "supersecurepw123",
                "cms_role": "viewer",
            },
        )
        assert resp.status_code == 403
