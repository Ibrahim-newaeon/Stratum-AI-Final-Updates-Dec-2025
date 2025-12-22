"""
Stratum AI - Campaign Tests
Tests for campaign CRUD operations and metrics.
"""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, CampaignStatus, AdPlatform, Tenant, User


class TestCampaignList:
    """Tests for listing campaigns."""

    @pytest.mark.asyncio
    async def test_list_campaigns_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing campaigns when none exist."""
        response = await client.get(
            "/api/v1/campaigns",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["items"] == []
        assert data["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_list_campaigns_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test listing campaigns with existing data."""
        # Create test campaigns
        campaigns = [
            Campaign(
                tenant_id=test_tenant.id,
                name="Summer Sale 2024",
                external_id="ext_001",
                account_id="acc_001",
                platform=AdPlatform.META,
                status=CampaignStatus.ACTIVE,
                objective="conversions",
            ),
            Campaign(
                tenant_id=test_tenant.id,
                name="Brand Awareness Q4",
                external_id="ext_002",
                account_id="acc_001",
                platform=AdPlatform.GOOGLE,
                status=CampaignStatus.ACTIVE,
                objective="awareness",
            ),
        ]
        for campaign in campaigns:
            async_session.add(campaign)
        await async_session.commit()

        response = await client.get(
            "/api/v1/campaigns",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 2
        assert len(data["data"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test campaign list pagination."""
        # Create 15 test campaigns
        for i in range(15):
            campaign = Campaign(
                tenant_id=test_tenant.id,
                name=f"Campaign {i}",
                external_id=f"ext_{i:03d}",
                account_id="acc_001",
                platform=AdPlatform.META,
                status=CampaignStatus.ACTIVE,
            )
            async_session.add(campaign)
        await async_session.commit()

        # Get first page
        response = await client.get(
            "/api/v1/campaigns",
            params={"page": 1, "page_size": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 15
        assert len(data["data"]["items"]) == 10
        assert data["data"]["page"] == 1

        # Get second page
        response = await client.get(
            "/api/v1/campaigns",
            params={"page": 2, "page_size": 10},
            headers=auth_headers,
        )

        data = response.json()
        assert len(data["data"]["items"]) == 5
        assert data["data"]["page"] == 2

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_by_platform(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test filtering campaigns by platform."""
        # Create campaigns on different platforms
        campaigns = [
            Campaign(
                tenant_id=test_tenant.id,
                name="Meta Campaign",
                external_id="ext_meta",
                account_id="acc_001",
                platform=AdPlatform.META,
                status=CampaignStatus.ACTIVE,
            ),
            Campaign(
                tenant_id=test_tenant.id,
                name="Google Campaign",
                external_id="ext_google",
                account_id="acc_001",
                platform=AdPlatform.GOOGLE,
                status=CampaignStatus.ACTIVE,
            ),
        ]
        for campaign in campaigns:
            async_session.add(campaign)
        await async_session.commit()

        response = await client.get(
            "/api/v1/campaigns",
            params={"platform": "meta"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["platform"] == "meta"

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test filtering campaigns by status."""
        # Create campaigns with different statuses
        campaigns = [
            Campaign(
                tenant_id=test_tenant.id,
                name="Active Campaign",
                external_id="ext_active",
                account_id="acc_001",
                platform=AdPlatform.META,
                status=CampaignStatus.ACTIVE,
            ),
            Campaign(
                tenant_id=test_tenant.id,
                name="Paused Campaign",
                external_id="ext_paused",
                account_id="acc_001",
                platform=AdPlatform.META,
                status=CampaignStatus.PAUSED,
            ),
        ]
        for campaign in campaigns:
            async_session.add(campaign)
        await async_session.commit()

        response = await client.get(
            "/api/v1/campaigns",
            params={"status": "active"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_campaigns_unauthorized(self, client: AsyncClient):
        """Test listing campaigns without authentication."""
        response = await client.get("/api/v1/campaigns")

        assert response.status_code == 401


class TestCampaignCreate:
    """Tests for creating campaigns."""

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful campaign creation."""
        campaign_data = {
            "name": "New Campaign",
            "external_id": "ext_new",
            "account_id": "acc_001",
            "platform": "meta",
            "status": "draft",
            "objective": "conversions",
            "daily_budget_cents": 10000,
            "currency": "USD",
        }

        response = await client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Campaign"
        assert data["data"]["platform"] == "meta"

    @pytest.mark.asyncio
    async def test_create_campaign_with_targeting(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test campaign creation with targeting options."""
        campaign_data = {
            "name": "Targeted Campaign",
            "external_id": "ext_targeted",
            "account_id": "acc_001",
            "platform": "meta",
            "status": "draft",
            "targeting_age_min": 18,
            "targeting_age_max": 45,
            "targeting_genders": ["male", "female"],
            "targeting_locations": [{"country": "US"}, {"country": "UK"}],
        }

        response = await client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["targeting_age_min"] == 18
        assert data["data"]["targeting_age_max"] == 45

    @pytest.mark.asyncio
    async def test_create_campaign_with_dates(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test campaign creation with start and end dates."""
        start_date = date.today()
        end_date = date.today() + timedelta(days=30)

        campaign_data = {
            "name": "Scheduled Campaign",
            "external_id": "ext_scheduled",
            "account_id": "acc_001",
            "platform": "google",
            "status": "draft",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        response = await client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["start_date"] == start_date.isoformat()
        assert data["data"]["end_date"] == end_date.isoformat()

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_dates(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test campaign creation with end_date before start_date."""
        start_date = date.today() + timedelta(days=30)
        end_date = date.today()  # Before start

        campaign_data = {
            "name": "Invalid Dates Campaign",
            "external_id": "ext_invalid",
            "account_id": "acc_001",
            "platform": "meta",
            "status": "draft",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        response = await client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_age_range(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test campaign creation with invalid age range."""
        campaign_data = {
            "name": "Invalid Age Campaign",
            "external_id": "ext_age",
            "account_id": "acc_001",
            "platform": "meta",
            "status": "draft",
            "targeting_age_min": 45,
            "targeting_age_max": 18,  # Less than min
        }

        response = await client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_missing_required_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test campaign creation with missing required fields."""
        campaign_data = {
            "name": "Incomplete Campaign",
            # Missing external_id, account_id, platform
        }

        response = await client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestCampaignGet:
    """Tests for getting a single campaign."""

    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test getting an existing campaign."""
        campaign = Campaign(
            tenant_id=test_tenant.id,
            name="Test Campaign",
            external_id="ext_test",
            account_id="acc_001",
            platform=AdPlatform.META,
            status=CampaignStatus.ACTIVE,
            impressions=10000,
            clicks=500,
            conversions=50,
        )
        async_session.add(campaign)
        await async_session.commit()
        await async_session.refresh(campaign)

        response = await client.get(
            f"/api/v1/campaigns/{campaign.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Campaign"
        assert data["data"]["impressions"] == 10000

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a non-existent campaign."""
        response = await client.get(
            "/api/v1/campaigns/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestCampaignUpdate:
    """Tests for updating campaigns."""

    @pytest.mark.asyncio
    async def test_update_campaign_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test successful campaign update."""
        campaign = Campaign(
            tenant_id=test_tenant.id,
            name="Original Name",
            external_id="ext_update",
            account_id="acc_001",
            platform=AdPlatform.META,
            status=CampaignStatus.DRAFT,
        )
        async_session.add(campaign)
        await async_session.commit()
        await async_session.refresh(campaign)

        response = await client.put(
            f"/api/v1/campaigns/{campaign.id}",
            json={
                "name": "Updated Name",
                "status": "active",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_update_campaign_partial(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test partial campaign update."""
        campaign = Campaign(
            tenant_id=test_tenant.id,
            name="Original Name",
            external_id="ext_partial",
            account_id="acc_001",
            platform=AdPlatform.META,
            status=CampaignStatus.ACTIVE,
            daily_budget_cents=5000,
        )
        async_session.add(campaign)
        await async_session.commit()
        await async_session.refresh(campaign)

        # Only update budget
        response = await client.put(
            f"/api/v1/campaigns/{campaign.id}",
            json={"daily_budget_cents": 10000},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Original Name"  # Unchanged
        assert data["data"]["daily_budget_cents"] == 10000  # Updated

    @pytest.mark.asyncio
    async def test_update_campaign_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating a non-existent campaign."""
        response = await client.put(
            "/api/v1/campaigns/99999",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestCampaignDelete:
    """Tests for deleting campaigns."""

    @pytest.mark.asyncio
    async def test_delete_campaign_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test successful campaign deletion."""
        campaign = Campaign(
            tenant_id=test_tenant.id,
            name="To Delete",
            external_id="ext_delete",
            account_id="acc_001",
            platform=AdPlatform.META,
            status=CampaignStatus.DRAFT,
        )
        async_session.add(campaign)
        await async_session.commit()
        await async_session.refresh(campaign)

        response = await client.delete(
            f"/api/v1/campaigns/{campaign.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify campaign is deleted (soft delete)
        get_response = await client.get(
            f"/api/v1/campaigns/{campaign.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_campaign_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a non-existent campaign."""
        response = await client.delete(
            "/api/v1/campaigns/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestCampaignMetrics:
    """Tests for campaign metrics endpoints."""

    @pytest.mark.asyncio
    async def test_get_campaign_metrics(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test getting campaign metrics."""
        campaign = Campaign(
            tenant_id=test_tenant.id,
            name="Metrics Campaign",
            external_id="ext_metrics",
            account_id="acc_001",
            platform=AdPlatform.META,
            status=CampaignStatus.ACTIVE,
            impressions=100000,
            clicks=5000,
            conversions=500,
            total_spend_cents=50000,
            revenue_cents=200000,
        )
        async_session.add(campaign)
        await async_session.commit()
        await async_session.refresh(campaign)

        response = await client.get(
            f"/api/v1/campaigns/{campaign.id}/metrics",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTenantIsolation:
    """Tests for multi-tenant data isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_campaigns(
        self,
        client: AsyncClient,
        auth_headers: dict,
        async_session: AsyncSession,
    ):
        """Test that users cannot access campaigns from other tenants."""
        # Create another tenant
        other_tenant = Tenant(
            name="Other Company",
            slug="other-company",
            plan="free",
        )
        async_session.add(other_tenant)
        await async_session.commit()
        await async_session.refresh(other_tenant)

        # Create campaign for other tenant
        campaign = Campaign(
            tenant_id=other_tenant.id,
            name="Other Tenant Campaign",
            external_id="ext_other",
            account_id="acc_other",
            platform=AdPlatform.META,
            status=CampaignStatus.ACTIVE,
        )
        async_session.add(campaign)
        await async_session.commit()
        await async_session.refresh(campaign)

        # Try to access it with auth headers from test_tenant
        response = await client.get(
            f"/api/v1/campaigns/{campaign.id}",
            headers=auth_headers,
        )

        # Should not be accessible
        assert response.status_code == 404
