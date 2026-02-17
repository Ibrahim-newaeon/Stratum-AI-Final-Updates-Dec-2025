#!/usr/bin/env python3
"""
Stratum AI - Load Test User Seed Script

Creates a test user for k6 load testing.

Usage:
    docker compose exec api python scripts/seed_load_test_user.py

Credentials created:
    Email:    admin@test-tenant.com
    Password: TestPassword123!
    Tenant:   Load Test Tenant (ID: 1 or first available)
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup
from app.models import AdPlatform, Tenant, User, UserRole
from app.models.campaign_builder import (
    ConnectionStatus,
    TenantAdAccount,
    TenantPlatformConnection,
)
from app.models.onboarding import (
    AutomationMode,
    Industry,
    MonthlyAdSpend,
    OnboardingStatus,
    OnboardingStep,
    PrimaryKPI,
    TeamSize,
    TenantOnboarding,
)

# Load test user credentials (matches k6 test defaults)
TEST_EMAIL = "admin@test-tenant.com"
TEST_PASSWORD = "TestPassword123!"
TEST_TENANT_NAME = "Load Test Tenant"
TEST_TENANT_SLUG = "load-test-tenant"


async def seed_load_test_user():
    """Create load test user and tenant."""

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("  Stratum AI - Load Test User Setup")
    print("=" * 60)

    async with async_session() as db:
        try:
            # Check if test user already exists
            email_hash = hash_pii_for_lookup(TEST_EMAIL.lower())
            result = await db.execute(select(User).where(User.email_hash == email_hash))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"\n[!] Load test user already exists (ID: {existing_user.id})")
                print(f"    Email: {TEST_EMAIL}")
                print(f"    Tenant ID: {existing_user.tenant_id}")
                print("\n    To reset, delete the user and run this script again.")
                return

            # Check for existing tenant with ID 1 or create new one
            result = await db.execute(select(Tenant).where(Tenant.id == 1))
            tenant = result.scalar_one_or_none()

            if not tenant:
                # Check for tenant by slug
                result = await db.execute(select(Tenant).where(Tenant.slug == TEST_TENANT_SLUG))
                tenant = result.scalar_one_or_none()

            if not tenant:
                print("\n[1/4] Creating load test tenant...")
                tenant = Tenant(
                    name=TEST_TENANT_NAME,
                    slug=TEST_TENANT_SLUG,
                    settings={"timezone": "UTC", "currency": "USD"},
                )
                db.add(tenant)
                await db.flush()
                print(f"      Created tenant: {tenant.name} (ID: {tenant.id})")
            else:
                print(f"\n[1/4] Using existing tenant: {tenant.name} (ID: {tenant.id})")

            print("\n[2/4] Creating load test user...")
            user = User(
                email=encrypt_pii(TEST_EMAIL.lower()),
                email_hash=email_hash,
                password_hash=get_password_hash(TEST_PASSWORD),
                full_name=encrypt_pii("Load Test Admin"),
                role=UserRole.ADMIN,
                tenant_id=tenant.id,
                is_verified=True,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            print(f"      Created user: {TEST_EMAIL}")
            print(f"      User ID: {user.id}")
            print(f"      Role: {user.role.value}")

            # Check if onboarding exists for this tenant
            result = await db.execute(
                select(TenantOnboarding).where(TenantOnboarding.tenant_id == tenant.id)
            )
            onboarding = result.scalar_one_or_none()

            if not onboarding:
                print("\n[3/4] Creating onboarding record...")
                onboarding = TenantOnboarding(
                    tenant_id=tenant.id,
                    status=OnboardingStatus.COMPLETED.value,
                    current_step=OnboardingStep.TRUST_GATE_CONFIG.value,
                    completed_steps=[s.value for s in OnboardingStep],
                    industry=Industry.ECOMMERCE.value,
                    monthly_ad_spend=MonthlyAdSpend.FROM_10K_50K.value,
                    team_size=TeamSize.SMALL.value,
                    primary_kpi=PrimaryKPI.ROAS.value,
                    target_roas=3.0,
                    automation_mode=AutomationMode.ASSISTED.value,
                    trust_threshold_autopilot=70,
                    trust_threshold_alert=40,
                    selected_platforms=["meta", "google"],
                )
                db.add(onboarding)
                await db.flush()
                print("      Onboarding completed")
            else:
                print("\n[3/4] Onboarding already exists for tenant")

            # Check if platform connections exist
            result = await db.execute(
                select(TenantPlatformConnection).where(
                    TenantPlatformConnection.tenant_id == tenant.id
                )
            )
            connections = result.scalars().all()

            if not connections:
                print("\n[4/4] Creating platform connections...")
                platforms = [
                    (AdPlatform.META, "Meta Ads", "act_test_123"),
                    (AdPlatform.GOOGLE, "Google Ads", "test-123-456"),
                ]

                for platform, name, account_id in platforms:
                    connection = TenantPlatformConnection(
                        tenant_id=tenant.id,
                        platform=platform.value,
                        status=ConnectionStatus.CONNECTED.value,
                        access_token_encrypted="test_token_" + platform.value,
                        refresh_token_encrypted="test_refresh_" + platform.value,
                        token_expires_at=datetime.now(UTC) + timedelta(days=60),
                        scopes=["ads_read", "ads_management"],
                        connected_at=datetime.now(UTC),
                        last_refreshed_at=datetime.now(UTC),
                    )
                    db.add(connection)
                    await db.flush()

                    ad_account = TenantAdAccount(
                        tenant_id=tenant.id,
                        connection_id=connection.id,
                        platform=platform.value,
                        platform_account_id=account_id,
                        name=f"{name} - Test Account",
                        currency="USD",
                        timezone="UTC",
                        is_enabled=True,
                    )
                    db.add(ad_account)
                    print(f"      Connected: {platform.value}")
            else:
                print("\n[4/4] Platform connections already exist")

            await db.commit()

            print("\n" + "=" * 60)
            print("  Load test user created successfully!")
            print("=" * 60)
            print("\n  Credentials for k6 load tests:")
            print(f"    Email:     {TEST_EMAIL}")
            print(f"    Password:  {TEST_PASSWORD}")
            print(f"    Tenant ID: {tenant.id}")
            print("\n  Run load tests with:")
            print("    k6 run --env SCENARIO=smoke tests/load/api-load-test.js")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[ERROR] Failed to create load test user: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_load_test_user())
