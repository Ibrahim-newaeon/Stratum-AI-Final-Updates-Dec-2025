"""
Stratum AI - EMQ One-Click Fix System Tests
Tests for fix suggestions, apply fixes, fix runs, and fix history.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, CapiQaLog, FixRun, TenantTrackingConfig
from app.services.fixes.catalog import (
    FIX_CATALOG,
    get_fix_metadata,
    get_all_one_click_fixes,
    get_all_guided_fixes,
)


# =============================================================================
# Fix Catalog Unit Tests
# =============================================================================
class TestFixCatalog:
    """Unit tests for the fix catalog."""

    def test_fix_catalog_has_required_issues(self):
        """Test that catalog contains all expected issue codes."""
        expected_codes = [
            "LOW_SUCCESS_RATE",
            "LOW_MATCH_SCORE",
            "HIGH_DUPLICATES",
            "LOW_EMAIL_COVERAGE",
            "LOW_PHONE_COVERAGE",
            "LOW_COOKIE_COVERAGE",
            "MISSING_IP_UA",
            "CLIENT_ID_DROP_GA4",
            "CONFIG_MISMATCH",
        ]
        for code in expected_codes:
            assert code in FIX_CATALOG, f"Missing issue code: {code}"

    def test_fix_catalog_structure(self):
        """Test that each fix has required fields."""
        required_fields = ["one_click", "action", "description"]

        for code, meta in FIX_CATALOG.items():
            for field in required_fields:
                assert field in meta, f"Missing field '{field}' in {code}"

    def test_fix_catalog_roas_impact(self):
        """Test that each fix has ROAS impact data."""
        for code, meta in FIX_CATALOG.items():
            assert "roas_impact" in meta, f"Missing roas_impact in {code}"
            roas = meta["roas_impact"]
            assert "min_pct" in roas, f"Missing min_pct in {code}"
            assert "max_pct" in roas, f"Missing max_pct in {code}"
            assert "avg_pct" in roas, f"Missing avg_pct in {code}"
            assert "confidence" in roas, f"Missing confidence in {code}"
            assert "reasoning" in roas, f"Missing reasoning in {code}"

            # Validate ranges
            assert roas["min_pct"] <= roas["avg_pct"] <= roas["max_pct"]
            assert roas["confidence"] in ["high", "medium", "low"]

    def test_get_fix_metadata(self):
        """Test getting fix metadata by code."""
        meta = get_fix_metadata("LOW_SUCCESS_RATE")
        assert meta is not None
        assert meta["action"] == "enable_retries"
        assert meta["one_click"] is True

    def test_get_fix_metadata_invalid_code(self):
        """Test getting metadata for invalid code returns None."""
        meta = get_fix_metadata("INVALID_CODE")
        assert meta is None

    def test_get_all_one_click_fixes(self):
        """Test getting list of one-click fixable issues."""
        one_click = get_all_one_click_fixes()
        assert isinstance(one_click, list)
        assert "LOW_SUCCESS_RATE" in one_click
        assert "LOW_MATCH_SCORE" in one_click
        assert "HIGH_DUPLICATES" in one_click
        # Guided fixes should NOT be in this list
        assert "LOW_EMAIL_COVERAGE" not in one_click

    def test_get_all_guided_fixes(self):
        """Test getting list of guided fix issues."""
        guided = get_all_guided_fixes()
        assert isinstance(guided, list)
        assert "LOW_EMAIL_COVERAGE" in guided
        assert "LOW_PHONE_COVERAGE" in guided
        assert "LOW_COOKIE_COVERAGE" in guided
        # One-click fixes should NOT be in this list
        assert "LOW_SUCCESS_RATE" not in guided

    def test_guided_fixes_have_steps(self):
        """Test that guided fixes include step-by-step instructions."""
        guided = get_all_guided_fixes()
        for code in guided:
            meta = FIX_CATALOG[code]
            assert "guided_steps" in meta, f"Missing guided_steps in {code}"
            assert len(meta["guided_steps"]) > 0, f"Empty guided_steps in {code}"


# =============================================================================
# Test Fixtures
# =============================================================================
@pytest.fixture
async def test_qa_logs(async_session: AsyncSession, test_tenant: Tenant):
    """Create test QA log entries for fix suggestions."""
    now = datetime.now(timezone.utc)
    logs = []

    # Create logs with varying quality to trigger different suggestions
    for i in range(100):
        log = CapiQaLog(
            tenant_id=test_tenant.id,
            platform="meta",
            event_name="Purchase",
            event_time=int((now - timedelta(hours=i)).timestamp()),
            event_id=f"evt_{i:04d}",
            action_source="website",
            # Varying success rates
            status="success" if i % 10 != 0 else "error",
            # Varying coverage
            has_email=i % 3 != 0,  # ~66% email coverage
            has_phone=i % 4 != 0,  # ~75% phone coverage
            has_external_id=i % 5 != 0,
            has_fbp=i % 6 != 0,  # Low cookie coverage
            has_fbc=i % 7 != 0,
            has_ip=True,
            has_ua=True,
            # EMQ score varies
            emq_score=40 + (i % 40),  # Range 40-79
            created_at=now - timedelta(hours=i),
        )
        logs.append(log)
        async_session.add(log)

    await async_session.commit()
    return logs


@pytest.fixture
async def test_tracking_config(async_session: AsyncSession, test_tenant: Tenant):
    """Create test tracking configuration."""
    config = TenantTrackingConfig(
        tenant_id=test_tenant.id,
        platform="meta",
        normalization_policy="v1",
        retry_enabled=False,
        max_retries=1,
        backoff_seconds=1,
        dedupe_mode="capi_only",
    )
    async_session.add(config)
    await async_session.commit()
    await async_session.refresh(config)
    return config


# =============================================================================
# API Endpoint Tests - Suggestions
# =============================================================================
class TestFixSuggestions:
    """Tests for the fix suggestions endpoint."""

    @pytest.mark.asyncio
    async def test_get_suggestions_success(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test getting fix suggestions."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/qa/fixes/suggestions?platform=meta&from={week_ago}&to={today}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "tenant_id" in data
        assert "platform" in data
        assert "metrics" in data
        assert "items" in data
        assert "suggestion_count" in data
        assert data["platform"] == "meta"

    @pytest.mark.asyncio
    async def test_get_suggestions_with_event_filter(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test getting suggestions filtered by event name."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/qa/fixes/suggestions?platform=meta&from={week_ago}&to={today}&event_name=Purchase"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_name"] == "Purchase"

    @pytest.mark.asyncio
    async def test_get_suggestions_metrics_computed(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test that metrics are properly computed."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/qa/fixes/suggestions?platform=meta&from={week_ago}&to={today}"
        )

        assert response.status_code == 200
        metrics = response.json()["metrics"]

        assert "events" in metrics
        assert "success_rate" in metrics
        assert "avg_score" in metrics
        assert "duplicate_rate" in metrics
        assert "coverage" in metrics

        # Validate coverage has expected fields
        coverage = metrics["coverage"]
        assert "em" in coverage  # email
        assert "ph" in coverage  # phone
        assert "fbp" in coverage  # cookie
        assert "ip" in coverage
        assert "ua" in coverage

    @pytest.mark.asyncio
    async def test_get_suggestions_includes_roas_impact(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test that suggestions include ROAS impact data."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/qa/fixes/suggestions?platform=meta&from={week_ago}&to={today}"
        )

        assert response.status_code == 200
        items = response.json()["items"]

        for item in items:
            assert "roas_impact" in item
            roas = item["roas_impact"]
            assert "min_pct" in roas
            assert "max_pct" in roas
            assert "confidence" in roas
            assert "reasoning" in roas

    @pytest.mark.asyncio
    async def test_get_suggestions_no_data(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test suggestions when no QA logs exist."""
        response = await client.get(
            "/api/v1/qa/fixes/suggestions?platform=meta&from=2025-01-01&to=2025-01-07"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["suggestion_count"] == 0

    @pytest.mark.asyncio
    async def test_get_suggestions_missing_platform(self, client: AsyncClient):
        """Test suggestions without required platform parameter."""
        response = await client.get(
            "/api/v1/qa/fixes/suggestions?from=2025-01-01&to=2025-01-07"
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_suggestions_missing_date_range(self, client: AsyncClient):
        """Test suggestions without required date parameters."""
        response = await client.get(
            "/api/v1/qa/fixes/suggestions?platform=meta"
        )

        assert response.status_code == 422  # Validation error


# =============================================================================
# API Endpoint Tests - Apply Fix
# =============================================================================
class TestApplyFix:
    """Tests for the apply fix endpoint."""

    @pytest.mark.asyncio
    async def test_apply_one_click_fix_success(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs, test_tracking_config
    ):
        """Test applying a one-click fix successfully."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "LOW_SUCCESS_RATE",
                "dry_run": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert "fix_run_id" in data
        assert "applied" in data
        assert "before_metrics" in data
        assert "after_metrics" in data
        assert data["status"] == "success"

        # Verify retry was enabled
        assert data["applied"]["retry_enabled"] is True

    @pytest.mark.asyncio
    async def test_apply_fix_dry_run(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test dry run mode shows changes without applying."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "LOW_MATCH_SCORE",
                "dry_run": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert data["dry_run"] is True
        assert "would_apply" in data
        assert data["would_apply"] == "set_normalization_v2"

    @pytest.mark.asyncio
    async def test_apply_fix_creates_audit_record(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs
    ):
        """Test that applying a fix creates an audit record."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "HIGH_DUPLICATES",
                "dry_run": False,
            },
        )

        assert response.status_code == 200
        fix_run_id = response.json()["fix_run_id"]

        # Verify audit record exists
        from sqlalchemy import select
        result = await async_session.execute(
            select(FixRun).where(FixRun.id == fix_run_id)
        )
        run = result.scalar_one_or_none()

        assert run is not None
        assert run.issue_code == "HIGH_DUPLICATES"
        assert run.action == "enforce_event_id"
        assert run.status == "success"

    @pytest.mark.asyncio
    async def test_apply_fix_projected_roas(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test that fix includes projected ROAS improvement."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "LOW_MATCH_SCORE",
                "dry_run": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check ROAS projections
        assert "projected_roas" in data["before_metrics"]
        assert "projected_roas" in data["after_metrics"]
        assert "roas_improvement_pct" in data["after_metrics"]

        # After should be higher than before
        assert data["after_metrics"]["projected_roas"] > data["before_metrics"]["projected_roas"]

    @pytest.mark.asyncio
    async def test_apply_guided_fix_returns_steps(
        self, client: AsyncClient, test_tenant: Tenant, test_qa_logs
    ):
        """Test that guided fixes return step-by-step instructions."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "LOW_EMAIL_COVERAGE",
                "dry_run": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is False
        assert "guided_steps" in data
        assert len(data["guided_steps"]) > 0
        assert "message" in data

    @pytest.mark.asyncio
    async def test_apply_fix_invalid_issue_code(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test applying fix with invalid issue code."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "INVALID_CODE",
                "dry_run": False,
            },
        )

        assert response.status_code == 400
        assert "Unknown issue_code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_apply_fix_creates_config_if_missing(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs
    ):
        """Test that applying fix creates config if it doesn't exist."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "tiktok",  # No existing config
                "issue_code": "LOW_SUCCESS_RATE",
                "dry_run": False,
            },
        )

        assert response.status_code == 200

        # Verify config was created
        from sqlalchemy import select
        result = await async_session.execute(
            select(TenantTrackingConfig).where(
                TenantTrackingConfig.tenant_id == test_tenant.id,
                TenantTrackingConfig.platform == "tiktok",
            )
        )
        config = result.scalar_one_or_none()
        assert config is not None


# =============================================================================
# API Endpoint Tests - Fix Run Status
# =============================================================================
class TestFixRunStatus:
    """Tests for the fix run status endpoint."""

    @pytest.mark.asyncio
    async def test_get_fix_run_success(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant
    ):
        """Test getting fix run status."""
        # Create a fix run
        run = FixRun(
            tenant_id=test_tenant.id,
            platform="meta",
            issue_code="LOW_SUCCESS_RATE",
            action="enable_retries",
            status="success",
            applied_changes={"retry_enabled": True},
            before_metrics={"success_rate": 0.85},
            after_metrics={"success_rate": 0.92},
        )
        async_session.add(run)
        await async_session.commit()
        await async_session.refresh(run)

        response = await client.get(f"/api/v1/qa/fixes/run/{run.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == run.id
        assert data["platform"] == "meta"
        assert data["issue_code"] == "LOW_SUCCESS_RATE"
        assert data["status"] == "success"
        assert data["applied_changes"]["retry_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_fix_run_not_found(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test getting non-existent fix run."""
        response = await client.get("/api/v1/qa/fixes/run/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_fix_run_wrong_tenant(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Test that users cannot access other tenants' fix runs."""
        # Create a fix run for a different tenant
        other_run = FixRun(
            tenant_id=99999,  # Different tenant
            platform="meta",
            issue_code="LOW_SUCCESS_RATE",
            action="enable_retries",
            status="success",
        )
        async_session.add(other_run)
        await async_session.commit()
        await async_session.refresh(other_run)

        response = await client.get(f"/api/v1/qa/fixes/run/{other_run.id}")

        assert response.status_code == 404  # Should not find it


# =============================================================================
# API Endpoint Tests - Fix History
# =============================================================================
class TestFixHistory:
    """Tests for the fix history endpoint."""

    @pytest.mark.asyncio
    async def test_get_fix_history(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant
    ):
        """Test getting fix history."""
        # Create multiple fix runs
        for i in range(5):
            run = FixRun(
                tenant_id=test_tenant.id,
                platform="meta",
                issue_code=f"ISSUE_{i}",
                action=f"action_{i}",
                status="success",
                created_at=datetime.now(timezone.utc) - timedelta(hours=i),
            )
            async_session.add(run)
        await async_session.commit()

        response = await client.get("/api/v1/qa/fixes/history")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) == 5

        # Should be ordered by created_at desc
        for i, item in enumerate(data["items"]):
            assert item["issue_code"] == f"ISSUE_{i}"

    @pytest.mark.asyncio
    async def test_get_fix_history_with_platform_filter(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant
    ):
        """Test getting fix history filtered by platform."""
        # Create runs for different platforms
        for platform in ["meta", "meta", "tiktok", "google"]:
            run = FixRun(
                tenant_id=test_tenant.id,
                platform=platform,
                issue_code="TEST",
                action="test",
                status="success",
            )
            async_session.add(run)
        await async_session.commit()

        response = await client.get("/api/v1/qa/fixes/history?platform=meta")

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "meta"
        assert len(data["items"]) == 2
        for item in data["items"]:
            assert item["platform"] == "meta"

    @pytest.mark.asyncio
    async def test_get_fix_history_with_limit(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant
    ):
        """Test getting fix history with limit."""
        # Create 10 fix runs
        for i in range(10):
            run = FixRun(
                tenant_id=test_tenant.id,
                platform="meta",
                issue_code=f"ISSUE_{i}",
                action="test",
                status="success",
            )
            async_session.add(run)
        await async_session.commit()

        response = await client.get("/api/v1/qa/fixes/history?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_fix_history_empty(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test getting empty fix history."""
        response = await client.get("/api/v1/qa/fixes/history")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []


# =============================================================================
# Configuration Update Tests
# =============================================================================
class TestConfigurationUpdates:
    """Tests for verifying configuration changes after fixes."""

    @pytest.mark.asyncio
    async def test_enable_retries_updates_config(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs, test_tracking_config
    ):
        """Test that enable_retries fix updates configuration correctly."""
        # Apply the fix
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "LOW_SUCCESS_RATE",
                "dry_run": False,
            },
        )
        assert response.status_code == 200

        # Verify config was updated
        await async_session.refresh(test_tracking_config)

        assert test_tracking_config.retry_enabled is True
        assert test_tracking_config.max_retries >= 3
        assert test_tracking_config.backoff_seconds >= 2

    @pytest.mark.asyncio
    async def test_set_normalization_updates_config(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs, test_tracking_config
    ):
        """Test that normalization fix updates configuration correctly."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "LOW_MATCH_SCORE",
                "dry_run": False,
            },
        )
        assert response.status_code == 200

        await async_session.refresh(test_tracking_config)
        assert test_tracking_config.normalization_policy == "v2"

    @pytest.mark.asyncio
    async def test_enforce_event_id_updates_config(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs, test_tracking_config
    ):
        """Test that enforce_event_id fix updates configuration correctly."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "HIGH_DUPLICATES",
                "dry_run": False,
            },
        )
        assert response.status_code == 200

        await async_session.refresh(test_tracking_config)
        assert test_tracking_config.extra is not None
        assert test_tracking_config.extra.get("enforce_event_id") is True
        assert test_tracking_config.extra.get("dedupe_strict") is True

    @pytest.mark.asyncio
    async def test_enable_proxy_headers_updates_config(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs, test_tracking_config
    ):
        """Test that enable_proxy_headers fix updates configuration correctly."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "MISSING_IP_UA",
                "dry_run": False,
            },
        )
        assert response.status_code == 200

        await async_session.refresh(test_tracking_config)
        assert test_tracking_config.extra is not None
        assert test_tracking_config.extra.get("trust_proxy_headers") is True

    @pytest.mark.asyncio
    async def test_reset_config_updates_all(
        self, client: AsyncClient, async_session: AsyncSession,
        test_tenant: Tenant, test_qa_logs, test_tracking_config
    ):
        """Test that reset_config fix resets all settings to optimal."""
        response = await client.post(
            "/api/v1/qa/fixes/apply",
            json={
                "platform": "meta",
                "issue_code": "CONFIG_MISMATCH",
                "dry_run": False,
            },
        )
        assert response.status_code == 200

        await async_session.refresh(test_tracking_config)

        assert test_tracking_config.normalization_policy == "v2"
        assert test_tracking_config.retry_enabled is True
        assert test_tracking_config.max_retries == 3
        assert test_tracking_config.backoff_seconds == 2
        assert test_tracking_config.dedupe_mode == "capi_only"
        assert test_tracking_config.extra.get("enforce_event_id") is True
