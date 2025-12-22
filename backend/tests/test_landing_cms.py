"""
Stratum AI - Landing Page CMS Tests
Tests for content management, versioning, publishing, and multi-language support.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LandingContent, LandingContentHistory


# =============================================================================
# Test Fixtures
# =============================================================================
@pytest.fixture
async def test_content(async_session: AsyncSession):
    """Create test landing page content."""
    content = LandingContent(
        section="hero",
        language="en",
        content={
            "title": "Welcome to Stratum AI",
            "subtitle": "Optimize your ad performance",
            "cta_text": "Get Started",
        },
        is_published=True,
        version=1,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(content)
    await async_session.commit()
    await async_session.refresh(content)
    return content


@pytest.fixture
async def test_content_arabic(async_session: AsyncSession):
    """Create test Arabic content."""
    content = LandingContent(
        section="hero",
        language="ar",
        content={
            "title": "مرحباً بك في Stratum AI",
            "subtitle": "حسّن أداء إعلاناتك",
            "cta_text": "ابدأ الآن",
        },
        is_published=True,
        version=1,
    )
    async_session.add(content)
    await async_session.commit()
    await async_session.refresh(content)
    return content


@pytest.fixture
async def test_unpublished_content(async_session: AsyncSession):
    """Create unpublished content for testing."""
    content = LandingContent(
        section="features",
        language="en",
        content={
            "items": [
                {"title": "Feature 1", "description": "Description 1"},
                {"title": "Feature 2", "description": "Description 2"},
            ]
        },
        is_published=False,
        version=1,
    )
    async_session.add(content)
    await async_session.commit()
    await async_session.refresh(content)
    return content


@pytest.fixture
async def test_multiple_sections(async_session: AsyncSession):
    """Create multiple sections for testing."""
    sections = []
    for section in ["hero", "features", "pricing", "testimonials"]:
        content = LandingContent(
            section=section,
            language="en",
            content={"title": f"{section} Title"},
            is_published=True,
            version=1,
        )
        async_session.add(content)
        sections.append(content)

    await async_session.commit()
    for s in sections:
        await async_session.refresh(s)
    return sections


# =============================================================================
# Public Endpoint Tests
# =============================================================================
class TestPublicEndpoints:
    """Tests for public (unauthenticated) CMS endpoints."""

    @pytest.mark.asyncio
    async def test_get_all_published_content(
        self, client: AsyncClient, test_multiple_sections
    ):
        """Test getting all published content."""
        response = await client.get("/api/v1/landing-cms/public/all?language=en")

        assert response.status_code == 200
        data = response.json()

        assert "sections" in data
        assert "hero" in data["sections"]
        assert "features" in data["sections"]
        assert "pricing" in data["sections"]

    @pytest.mark.asyncio
    async def test_get_all_published_excludes_unpublished(
        self, client: AsyncClient, test_content, test_unpublished_content
    ):
        """Test that unpublished content is not returned."""
        response = await client.get("/api/v1/landing-cms/public/all?language=en")

        assert response.status_code == 200
        data = response.json()

        assert "hero" in data["sections"]
        assert "features" not in data["sections"]  # Unpublished

    @pytest.mark.asyncio
    async def test_get_all_published_by_language(
        self, client: AsyncClient, test_content, test_content_arabic
    ):
        """Test getting content by language."""
        # English
        en_response = await client.get("/api/v1/landing-cms/public/all?language=en")
        assert en_response.status_code == 200
        en_data = en_response.json()
        assert en_data["sections"]["hero"]["title"] == "Welcome to Stratum AI"

        # Arabic
        ar_response = await client.get("/api/v1/landing-cms/public/all?language=ar")
        assert ar_response.status_code == 200
        ar_data = ar_response.json()
        assert ar_data["sections"]["hero"]["title"] == "مرحباً بك في Stratum AI"

    @pytest.mark.asyncio
    async def test_get_published_section(
        self, client: AsyncClient, test_content
    ):
        """Test getting a specific published section."""
        response = await client.get(
            "/api/v1/landing-cms/public/hero?language=en"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "Welcome to Stratum AI"
        assert data["subtitle"] == "Optimize your ad performance"

    @pytest.mark.asyncio
    async def test_get_published_section_not_found(
        self, client: AsyncClient
    ):
        """Test getting non-existent section returns empty."""
        response = await client.get(
            "/api/v1/landing-cms/public/nonexistent?language=en"
        )

        assert response.status_code == 200
        data = response.json()
        assert data == {}

    @pytest.mark.asyncio
    async def test_get_unpublished_section_returns_empty(
        self, client: AsyncClient, test_unpublished_content
    ):
        """Test that unpublished sections return empty for public."""
        response = await client.get(
            "/api/v1/landing-cms/public/features?language=en"
        )

        assert response.status_code == 200
        data = response.json()
        assert data == {}


# =============================================================================
# Admin Endpoint Tests - List & Read
# =============================================================================
class TestAdminListEndpoints:
    """Tests for admin list and read endpoints."""

    @pytest.mark.asyncio
    async def test_list_all_sections(
        self, client: AsyncClient, test_multiple_sections
    ):
        """Test listing all sections."""
        response = await client.get("/api/v1/landing-cms/admin/sections")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 4  # hero, features, pricing, testimonials

    @pytest.mark.asyncio
    async def test_list_sections_by_language(
        self, client: AsyncClient, test_content, test_content_arabic
    ):
        """Test listing sections filtered by language."""
        response = await client.get(
            "/api/v1/landing-cms/admin/sections?language=ar"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["language"] == "ar"

    @pytest.mark.asyncio
    async def test_get_section_all_languages(
        self, client: AsyncClient, test_content, test_content_arabic
    ):
        """Test getting section in all languages."""
        response = await client.get("/api/v1/landing-cms/admin/section/hero")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        languages = [item["language"] for item in data]
        assert "en" in languages
        assert "ar" in languages

    @pytest.mark.asyncio
    async def test_get_section_by_language(
        self, client: AsyncClient, test_content
    ):
        """Test getting specific section by language."""
        response = await client.get(
            "/api/v1/landing-cms/admin/section/hero/en"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["section"] == "hero"
        assert data["language"] == "en"
        assert data["content"]["title"] == "Welcome to Stratum AI"

    @pytest.mark.asyncio
    async def test_get_section_not_found(self, client: AsyncClient):
        """Test getting non-existent section."""
        response = await client.get(
            "/api/v1/landing-cms/admin/section/nonexistent/en"
        )

        assert response.status_code == 404


# =============================================================================
# Admin Endpoint Tests - Create
# =============================================================================
class TestAdminCreateEndpoints:
    """Tests for admin create endpoints."""

    @pytest.mark.asyncio
    async def test_create_section(self, client: AsyncClient):
        """Test creating a new section."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "footer",
                "language": "en",
                "content": {
                    "copyright": "2025 Stratum AI",
                    "links": ["Privacy", "Terms"],
                },
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["section"] == "footer"
        assert data["language"] == "en"
        assert data["is_published"] is False
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_create_section_duplicate(
        self, client: AsyncClient, test_content
    ):
        """Test creating duplicate section/language fails."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "hero",  # Already exists
                "language": "en",   # Already exists
                "content": {"title": "Duplicate"},
            },
        )

        assert response.status_code == 409  # Conflict

    @pytest.mark.asyncio
    async def test_create_section_new_language(
        self, client: AsyncClient, test_content
    ):
        """Test creating section in new language."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "hero",  # Same section
                "language": "fr",   # New language
                "content": {"title": "Bienvenue"},
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["section"] == "hero"
        assert data["language"] == "fr"

    @pytest.mark.asyncio
    async def test_create_section_validation(self, client: AsyncClient):
        """Test section creation validation."""
        # Empty section name
        response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "",
                "language": "en",
                "content": {},
            },
        )
        assert response.status_code == 422


# =============================================================================
# Admin Endpoint Tests - Update
# =============================================================================
class TestAdminUpdateEndpoints:
    """Tests for admin update endpoints."""

    @pytest.mark.asyncio
    async def test_update_section(
        self, client: AsyncClient, test_content
    ):
        """Test updating section content."""
        response = await client.put(
            "/api/v1/landing-cms/admin/section/hero/en",
            json={
                "content": {
                    "title": "Updated Title",
                    "subtitle": "Updated Subtitle",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["content"]["title"] == "Updated Title"
        assert data["version"] == 2  # Version incremented

    @pytest.mark.asyncio
    async def test_update_creates_history(
        self, client: AsyncClient, async_session: AsyncSession, test_content
    ):
        """Test that updating creates a history record."""
        original_content = test_content.content.copy()

        # Update content
        await client.put(
            "/api/v1/landing-cms/admin/section/hero/en",
            json={"content": {"title": "New Title"}},
        )

        # Check history
        result = await async_session.execute(
            select(LandingContentHistory).where(
                LandingContentHistory.content_id == test_content.id
            )
        )
        history = result.scalars().all()

        assert len(history) == 1
        assert history[0].version == 1  # Original version
        assert history[0].content == original_content

    @pytest.mark.asyncio
    async def test_update_with_publish(
        self, client: AsyncClient, test_unpublished_content
    ):
        """Test updating and publishing simultaneously."""
        response = await client.put(
            "/api/v1/landing-cms/admin/section/features/en",
            json={
                "content": {"items": []},
                "is_published": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_published"] is True
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient):
        """Test updating non-existent section."""
        response = await client.put(
            "/api/v1/landing-cms/admin/section/nonexistent/en",
            json={"content": {}},
        )

        assert response.status_code == 404


# =============================================================================
# Admin Endpoint Tests - Publish/Unpublish
# =============================================================================
class TestPublishEndpoints:
    """Tests for publish/unpublish endpoints."""

    @pytest.mark.asyncio
    async def test_publish_section(
        self, client: AsyncClient, test_unpublished_content
    ):
        """Test publishing a section."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section/features/en/publish"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_published"] is True
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_unpublish_section(
        self, client: AsyncClient, test_content
    ):
        """Test unpublishing a section."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section/hero/en/unpublish"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_published"] is False

    @pytest.mark.asyncio
    async def test_publish_not_found(self, client: AsyncClient):
        """Test publishing non-existent section."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section/nonexistent/en/publish"
        )

        assert response.status_code == 404


# =============================================================================
# Admin Endpoint Tests - History & Rollback
# =============================================================================
class TestHistoryEndpoints:
    """Tests for history and rollback endpoints."""

    @pytest.mark.asyncio
    async def test_get_section_history(
        self, client: AsyncClient, async_session: AsyncSession, test_content
    ):
        """Test getting section history."""
        # Create some history by updating
        for i in range(3):
            await client.put(
                "/api/v1/landing-cms/admin/section/hero/en",
                json={"content": {"title": f"Version {i + 2}"}},
            )

        response = await client.get(
            "/api/v1/landing-cms/admin/section/hero/en/history"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3  # 3 previous versions
        # Should be ordered by version desc
        assert data[0]["version"] == 3
        assert data[1]["version"] == 2
        assert data[2]["version"] == 1

    @pytest.mark.asyncio
    async def test_get_history_with_limit(
        self, client: AsyncClient, async_session: AsyncSession, test_content
    ):
        """Test getting limited history."""
        # Create history
        for i in range(5):
            await client.put(
                "/api/v1/landing-cms/admin/section/hero/en",
                json={"content": {"title": f"Version {i + 2}"}},
            )

        response = await client.get(
            "/api/v1/landing-cms/admin/section/hero/en/history?limit=2"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_rollback_section(
        self, client: AsyncClient, async_session: AsyncSession, test_content
    ):
        """Test rolling back to a previous version."""
        original_title = test_content.content["title"]

        # Update to new content
        await client.put(
            "/api/v1/landing-cms/admin/section/hero/en",
            json={"content": {"title": "New Title"}},
        )

        # Rollback to version 1
        response = await client.post(
            "/api/v1/landing-cms/admin/section/hero/en/rollback/1"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["content"]["title"] == original_title
        assert data["version"] == 3  # Version increases on rollback

    @pytest.mark.asyncio
    async def test_rollback_invalid_version(
        self, client: AsyncClient, test_content
    ):
        """Test rolling back to non-existent version."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section/hero/en/rollback/999"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rollback_not_found(self, client: AsyncClient):
        """Test rollback on non-existent section."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section/nonexistent/en/rollback/1"
        )

        assert response.status_code == 404


# =============================================================================
# Admin Endpoint Tests - Delete
# =============================================================================
class TestDeleteEndpoints:
    """Tests for delete endpoints."""

    @pytest.mark.asyncio
    async def test_delete_section(
        self, client: AsyncClient, async_session: AsyncSession, test_content
    ):
        """Test deleting a section."""
        content_id = test_content.id

        response = await client.delete(
            "/api/v1/landing-cms/admin/section/hero/en"
        )

        assert response.status_code == 204

        # Verify deleted
        result = await async_session.execute(
            select(LandingContent).where(LandingContent.id == content_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_section_cascades_history(
        self, client: AsyncClient, async_session: AsyncSession, test_content
    ):
        """Test that deleting section also deletes history."""
        content_id = test_content.id

        # Create history
        await client.put(
            "/api/v1/landing-cms/admin/section/hero/en",
            json={"content": {"title": "Updated"}},
        )

        # Delete section
        await client.delete("/api/v1/landing-cms/admin/section/hero/en")

        # Verify history deleted
        result = await async_session.execute(
            select(LandingContentHistory).where(
                LandingContentHistory.content_id == content_id
            )
        )
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient):
        """Test deleting non-existent section."""
        response = await client.delete(
            "/api/v1/landing-cms/admin/section/nonexistent/en"
        )

        assert response.status_code == 404


# =============================================================================
# Utility Endpoint Tests
# =============================================================================
class TestUtilityEndpoints:
    """Tests for utility endpoints."""

    @pytest.mark.asyncio
    async def test_get_available_languages(
        self, client: AsyncClient, test_content, test_content_arabic
    ):
        """Test getting available languages."""
        response = await client.get("/api/v1/landing-cms/languages")

        assert response.status_code == 200
        data = response.json()

        assert "en" in data
        assert "ar" in data

    @pytest.mark.asyncio
    async def test_get_available_sections(
        self, client: AsyncClient, test_multiple_sections
    ):
        """Test getting available section types."""
        response = await client.get("/api/v1/landing-cms/sections")

        assert response.status_code == 200
        data = response.json()

        assert "hero" in data
        assert "features" in data
        assert "pricing" in data

    @pytest.mark.asyncio
    async def test_languages_empty(self, client: AsyncClient):
        """Test languages when no content exists."""
        response = await client.get("/api/v1/landing-cms/languages")

        assert response.status_code == 200
        data = response.json()

        assert data == []

    @pytest.mark.asyncio
    async def test_sections_empty(self, client: AsyncClient):
        """Test sections when no content exists."""
        response = await client.get("/api/v1/landing-cms/sections")

        assert response.status_code == 200
        data = response.json()

        assert data == []


# =============================================================================
# Content Validation Tests
# =============================================================================
class TestContentValidation:
    """Tests for content validation."""

    @pytest.mark.asyncio
    async def test_create_with_complex_content(self, client: AsyncClient):
        """Test creating section with complex nested content."""
        complex_content = {
            "title": "Complex Section",
            "items": [
                {
                    "id": 1,
                    "name": "Item 1",
                    "nested": {"key": "value"},
                },
                {
                    "id": 2,
                    "name": "Item 2",
                    "tags": ["tag1", "tag2"],
                },
            ],
            "metadata": {
                "created": "2025-01-01",
                "version": 1,
            },
        }

        response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "complex",
                "language": "en",
                "content": complex_content,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["content"] == complex_content

    @pytest.mark.asyncio
    async def test_update_preserves_content_structure(
        self, client: AsyncClient, test_content
    ):
        """Test that update properly preserves content structure."""
        new_content = {
            "title": "Updated",
            "subtitle": "Updated subtitle",
            "cta_text": "Updated CTA",
            "new_field": "New value",
        }

        response = await client.put(
            "/api/v1/landing-cms/admin/section/hero/en",
            json={"content": new_content},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["content"] == new_content

    @pytest.mark.asyncio
    async def test_empty_content_allowed(self, client: AsyncClient):
        """Test that empty content is allowed."""
        response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "empty",
                "language": "en",
                "content": {},
            },
        )

        assert response.status_code == 201
        assert response.json()["content"] == {}


# =============================================================================
# Multi-language Workflow Tests
# =============================================================================
class TestMultiLanguageWorkflow:
    """Tests for multi-language content workflow."""

    @pytest.mark.asyncio
    async def test_create_translate_publish_workflow(
        self, client: AsyncClient
    ):
        """Test complete workflow: create EN, translate to AR, publish both."""
        # 1. Create English version
        en_response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "about",
                "language": "en",
                "content": {"title": "About Us"},
            },
        )
        assert en_response.status_code == 201

        # 2. Create Arabic translation
        ar_response = await client.post(
            "/api/v1/landing-cms/admin/section",
            json={
                "section": "about",
                "language": "ar",
                "content": {"title": "نبذة عنا"},
            },
        )
        assert ar_response.status_code == 201

        # 3. Publish both
        await client.post("/api/v1/landing-cms/admin/section/about/en/publish")
        await client.post("/api/v1/landing-cms/admin/section/about/ar/publish")

        # 4. Verify both are available publicly
        en_public = await client.get("/api/v1/landing-cms/public/about?language=en")
        ar_public = await client.get("/api/v1/landing-cms/public/about?language=ar")

        assert en_public.json()["title"] == "About Us"
        assert ar_public.json()["title"] == "نبذة عنا"

    @pytest.mark.asyncio
    async def test_independent_language_publishing(
        self, client: AsyncClient, test_content, test_content_arabic
    ):
        """Test that language versions can be published independently."""
        # Unpublish English
        await client.post("/api/v1/landing-cms/admin/section/hero/en/unpublish")

        # Verify English is not public but Arabic is
        en_public = await client.get("/api/v1/landing-cms/public/hero?language=en")
        ar_public = await client.get("/api/v1/landing-cms/public/hero?language=ar")

        assert en_public.json() == {}  # Unpublished
        assert ar_public.json()["title"] == "مرحباً بك في Stratum AI"  # Still published
