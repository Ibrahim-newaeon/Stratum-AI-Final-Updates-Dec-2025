# =============================================================================
# Stratum AI - Landing CMS (public) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the public Landing CMS surface under
``/api/v1/landing-cms/...``: published pages, posts, categories, and tags.

These endpoints are unauthenticated (public marketing content). They filter by
published status — and previously referenced ``CMSPageStatus.published`` /
``CMSPostStatus.published`` (lowercase) while the enum members are uppercase
``PUBLISHED``, so every pages/posts read raised ``AttributeError`` → 500. The
listing tests seed published + draft rows to assert only published content is
returned.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/landing-cms"


async def _seed_page(db: AsyncSession, *, title: str, slug: str, published: bool):
    from app.models.cms import CMSPage, CMSPageStatus

    page = CMSPage(
        title=title,
        slug=slug,
        status=CMSPageStatus.PUBLISHED if published else CMSPageStatus.DRAFT,
    )
    db.add(page)
    await db.flush()
    return page


async def _seed_post(db: AsyncSession, *, title: str, slug: str, published: bool):
    from app.models.cms import CMSPost, CMSPostStatus

    post = CMSPost(
        title=title,
        slug=slug,
        status=CMSPostStatus.PUBLISHED if published else CMSPostStatus.DRAFT,
    )
    db.add(post)
    await db.flush()
    return post


class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestPages:
    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/pages")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["pages"] == []
        assert data["total"] == 0

    async def test_only_published_listed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_page(db_session, title="Home", slug="home", published=True)
        await _seed_page(db_session, title="Secret", slug="secret", published=False)

        resp = await client.get(f"{_BASE}/pages")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 1
        slugs = {p["slug"] for p in data["pages"]}
        assert slugs == {"home"}

    async def test_get_published_by_slug(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_page(db_session, title="About", slug="about", published=True)
        resp = await client.get(f"{_BASE}/pages/about")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["title"] == "About"

    async def test_draft_slug_404(self, client: AsyncClient, db_session: AsyncSession):
        await _seed_page(db_session, title="Draft", slug="draft-pg", published=False)
        resp = await client.get(f"{_BASE}/pages/draft-pg")
        assert resp.status_code == 404


class TestPosts:
    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/posts")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["total"] == 0

    async def test_only_published_listed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_post(db_session, title="Launch", slug="launch", published=True)
        await _seed_post(db_session, title="WIP", slug="wip", published=False)

        resp = await client.get(f"{_BASE}/posts")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["posts"][0]["slug"] == "launch"

    async def test_get_published_by_slug(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_post(db_session, title="Release Notes", slug="rel", published=True)
        resp = await client.get(f"{_BASE}/posts/rel")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["title"] == "Release Notes"
        # content_type is a plain string column (default "blog_post"), not an enum.
        assert data["content_type"] == "blog_post"

    async def test_draft_slug_404(self, client: AsyncClient, db_session: AsyncSession):
        await _seed_post(db_session, title="Hidden", slug="hidden", published=False)
        resp = await client.get(f"{_BASE}/posts/hidden")
        assert resp.status_code == 404


class TestTaxonomy:
    async def test_categories_empty(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/categories")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["categories"] == []

    async def test_tags_empty(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/tags")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["tags"] == []
