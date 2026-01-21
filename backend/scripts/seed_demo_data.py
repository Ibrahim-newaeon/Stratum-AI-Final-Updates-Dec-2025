#!/usr/bin/env python3
"""
Stratum AI - Demo Data Seed Script

This script populates the database with realistic demo data for testing
the unified dashboard. Run this after database migrations.

Usage:
    docker compose exec api python scripts/seed_demo_data.py

Or from the backend folder:
    python scripts/seed_demo_data.py
"""

import asyncio
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import (
    Tenant,
    User,
    UserRole,
    Campaign,
    CampaignStatus,
    AdPlatform,
    AuditLog,
    AuditAction,
)
from app.models.campaign_builder import (
    TenantPlatformConnection,
    TenantAdAccount,
    ConnectionStatus,
)
from app.models.onboarding import (
    TenantOnboarding,
    OnboardingStatus,
    OnboardingStep,
    Industry,
    MonthlyAdSpend,
    TeamSize,
    AutomationMode,
    PrimaryKPI,
)
from app.models.reporting import (
    ReportTemplate,
    ReportType,
    ReportFormat,
    ScheduledReport,
    ScheduleFrequency,
)
from app.core.security import get_password_hash, hash_pii_for_lookup, encrypt_pii


# Demo campaigns data - realistic ad campaigns
DEMO_CAMPAIGNS = [
    # High performers (ROAS > 3x) - Scale recommendations
    {
        "name": "Summer Sale - Lookalike Audiences",
        "platform": AdPlatform.META,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 4523_00,
        "revenue_cents": 18650_00,
        "conversions": 156,
        "impressions": 245000,
        "clicks": 4800,
    },
    {
        "name": "Brand Search - Exact Match",
        "platform": AdPlatform.GOOGLE,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 2150_00,
        "revenue_cents": 8900_00,
        "conversions": 89,
        "impressions": 45000,
        "clicks": 3200,
    },
    {
        "name": "Retargeting - Cart Abandoners",
        "platform": AdPlatform.META,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 1850_00,
        "revenue_cents": 7200_00,
        "conversions": 72,
        "impressions": 89000,
        "clicks": 2100,
    },
    # Medium performers (ROAS 1.5-3x) - Watch recommendations
    {
        "name": "Prospecting - Interest Targeting",
        "platform": AdPlatform.META,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 3200_00,
        "revenue_cents": 6100_00,
        "conversions": 45,
        "impressions": 320000,
        "clicks": 5600,
    },
    {
        "name": "Display - In-Market Audiences",
        "platform": AdPlatform.GOOGLE,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 1800_00,
        "revenue_cents": 3500_00,
        "conversions": 28,
        "impressions": 450000,
        "clicks": 2800,
    },
    {
        "name": "TikTok - Gen Z Awareness",
        "platform": AdPlatform.TIKTOK,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 2500_00,
        "revenue_cents": 4200_00,
        "conversions": 35,
        "impressions": 890000,
        "clicks": 12000,
    },
    # Low performers (ROAS < 1.5x) - Fix recommendations
    {
        "name": "Cold Audience - Broad Targeting",
        "platform": AdPlatform.META,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 2800_00,
        "revenue_cents": 2100_00,
        "conversions": 15,
        "impressions": 420000,
        "clicks": 3200,
    },
    {
        "name": "YouTube Pre-Roll - Awareness",
        "platform": AdPlatform.GOOGLE,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 1500_00,
        "revenue_cents": 800_00,
        "conversions": 8,
        "impressions": 250000,
        "clicks": 1200,
    },
    # Paused campaigns
    {
        "name": "Holiday Special - Expired",
        "platform": AdPlatform.META,
        "status": CampaignStatus.PAUSED,
        "spend_cents": 5200_00,
        "revenue_cents": 12000_00,
        "conversions": 95,
        "impressions": 180000,
        "clicks": 4500,
    },
    {
        "name": "Snapchat - Story Ads",
        "platform": AdPlatform.SNAPCHAT,
        "status": CampaignStatus.ACTIVE,
        "spend_cents": 1200_00,
        "revenue_cents": 2800_00,
        "conversions": 22,
        "impressions": 340000,
        "clicks": 8500,
    },
]

# Demo activity/audit log entries
DEMO_ACTIVITIES = [
    {"action": AuditAction.CREATE, "resource_type": "campaign", "resource_id": "1"},
    {"action": AuditAction.UPDATE, "resource_type": "campaign", "resource_id": "2"},
    {"action": AuditAction.LOGIN, "resource_type": "user", "resource_id": "1"},
    {"action": AuditAction.CREATE, "resource_type": "rule", "resource_id": "1"},
    {"action": AuditAction.UPDATE, "resource_type": "budget", "resource_id": "3"},
    {"action": AuditAction.CREATE, "resource_type": "campaign", "resource_id": "4"},
    {"action": AuditAction.UPDATE, "resource_type": "targeting", "resource_id": "1"},
    {"action": AuditAction.LOGIN, "resource_type": "user", "resource_id": "1"},
]

# Demo report templates
DEMO_REPORT_TEMPLATES = [
    {
        "name": "Weekly Performance Report",
        "description": "Comprehensive weekly summary of campaign performance across all platforms",
        "report_type": ReportType.CAMPAIGN_PERFORMANCE,
        "default_format": ReportFormat.PDF,
        "config": {
            "metrics": ["spend", "revenue", "roas", "conversions", "cpc", "cpm"],
            "dimensions": ["campaign", "platform", "date"],
            "sections": ["summary", "charts", "detailed_table", "recommendations"],
            "date_range": {"type": "last_7_days"},
        },
    },
    {
        "name": "Executive Summary",
        "description": "High-level overview for leadership with key metrics and trends",
        "report_type": ReportType.EXECUTIVE_SUMMARY,
        "default_format": ReportFormat.PDF,
        "config": {
            "metrics": ["total_spend", "total_revenue", "overall_roas", "top_campaigns"],
            "sections": ["kpi_summary", "trend_charts", "highlights"],
            "date_range": {"type": "last_30_days"},
        },
    },
    {
        "name": "Attribution Analysis",
        "description": "Multi-touch attribution breakdown by channel and campaign",
        "report_type": ReportType.ATTRIBUTION_SUMMARY,
        "default_format": ReportFormat.PDF,
        "config": {
            "metrics": ["attributed_conversions", "attributed_revenue", "channel_contribution"],
            "sections": ["funnel_analysis", "channel_comparison", "path_analysis"],
            "attribution_model": "data_driven",
        },
    },
    {
        "name": "Profit & ROAS Report",
        "description": "Detailed profit margin and ROAS analysis by campaign",
        "report_type": ReportType.PROFIT_ROAS,
        "default_format": ReportFormat.CSV,
        "config": {
            "metrics": ["spend", "revenue", "cogs", "profit", "profit_roas", "margin_percent"],
            "sections": ["profitability_table", "margin_trends"],
            "include_forecasts": True,
        },
    },
]


async def seed_demo_data():
    """Seed the database with demo data."""
    print("=" * 60)
    print("Stratum AI - Demo Data Seeder")
    print("=" * 60)

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Check if demo data already exists
            existing = await db.execute(
                select(User).where(User.email == "demo@stratum.ai")
            )
            if existing.scalar_one_or_none():
                print("\n[!] Demo data already exists. Skipping seed.")
                print("    To re-seed, delete the demo user first.")
                return

            print("\n[1/6] Creating demo tenant...")
            tenant = Tenant(
                name="Demo Company",
                slug="demo-company",
                settings={"timezone": "America/New_York", "currency": "USD"},
            )
            db.add(tenant)
            await db.flush()
            print(f"      Created tenant: {tenant.name} (ID: {tenant.id})")

            print("\n[2/6] Creating demo user...")
            demo_email = "demo@stratum.ai"
            email_hash = hash_pii_for_lookup(demo_email.lower())
            user = User(
                email=encrypt_pii(demo_email.lower()),
                email_hash=email_hash,
                password_hash=get_password_hash("demo1234"),
                full_name=encrypt_pii("Demo User"),
                role=UserRole.ADMIN,
                tenant_id=tenant.id,
                is_verified=True,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            print(f"      Created user: {demo_email} (password: demo1234)")

            print("\n[3/6] Creating onboarding record...")
            onboarding = TenantOnboarding(
                tenant_id=tenant.id,
                status=OnboardingStatus.COMPLETED.value,
                current_step=OnboardingStep.TRUST_GATE_CONFIG.value,
                completed_steps=[s.value for s in OnboardingStep],
                industry=Industry.ECOMMERCE.value,
                monthly_ad_spend=MonthlyAdSpend.FROM_50K_100K.value,
                team_size=TeamSize.MEDIUM.value,
                primary_kpi=PrimaryKPI.ROAS.value,
                target_roas=3.0,
                automation_mode=AutomationMode.AUTOPILOT.value,
                trust_threshold_autopilot=70,
                trust_threshold_alert=40,
                selected_platforms=["meta", "google", "tiktok", "snapchat"],
            )
            db.add(onboarding)
            await db.flush()
            print(f"      Onboarding completed with autopilot mode")

            print("\n[4/6] Creating platform connections...")
            platforms_to_connect = [
                (AdPlatform.META, "Meta Ads", "act_123456789"),
                (AdPlatform.GOOGLE, "Google Ads", "123-456-7890"),
                (AdPlatform.TIKTOK, "TikTok Ads", "tiktok_demo_123"),
                (AdPlatform.SNAPCHAT, "Snapchat Ads", "snap_demo_456"),
            ]

            for platform, name, account_id in platforms_to_connect:
                connection = TenantPlatformConnection(
                    tenant_id=tenant.id,
                    platform=platform.value,
                    status=ConnectionStatus.CONNECTED.value,
                    access_token_encrypted="demo_token_" + platform.value,
                    refresh_token_encrypted="demo_refresh_" + platform.value,
                    token_expires_at=datetime.now(timezone.utc) + timedelta(days=60),
                    scopes=["ads_read", "ads_management"],
                    connected_at=datetime.now(timezone.utc) - timedelta(days=30),
                    last_refreshed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                )
                db.add(connection)
                await db.flush()

                # Add ad account
                ad_account = TenantAdAccount(
                    tenant_id=tenant.id,
                    connection_id=connection.id,
                    platform=platform.value,
                    platform_account_id=account_id,
                    name=f"{name} - Demo Account",
                    currency="USD",
                    timezone="America/New_York",
                    is_enabled=True,
                )
                db.add(ad_account)
                print(f"      Connected: {platform.value} ({account_id})")

            await db.flush()

            # Map platforms to their account IDs
            platform_accounts = {
                AdPlatform.META: "act_123456789",
                AdPlatform.GOOGLE: "123-456-7890",
                AdPlatform.TIKTOK: "tiktok_demo_123",
                AdPlatform.SNAPCHAT: "snap_demo_456",
            }

            print("\n[5/6] Creating demo campaigns...")
            for i, campaign_data in enumerate(DEMO_CAMPAIGNS):
                campaign = Campaign(
                    tenant_id=tenant.id,
                    name=campaign_data["name"],
                    platform=campaign_data["platform"],
                    account_id=platform_accounts[campaign_data["platform"]],
                    external_id=f"ext_{campaign_data['platform'].value}_{i+1}",
                    status=campaign_data["status"],
                    objective="conversions",
                    total_spend_cents=campaign_data["spend_cents"],
                    revenue_cents=campaign_data["revenue_cents"],
                    conversions=campaign_data["conversions"],
                    impressions=campaign_data["impressions"],
                    clicks=campaign_data["clicks"],
                    is_deleted=False,
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(7, 60)),
                )
                db.add(campaign)

                # Calculate ROAS for display
                roas = campaign_data["revenue_cents"] / campaign_data["spend_cents"] if campaign_data["spend_cents"] > 0 else 0
                print(f"      {campaign_data['name'][:40]:<40} ROAS: {roas:.2f}x")

            await db.flush()

            print("\n[6/7] Creating report templates...")
            for template_data in DEMO_REPORT_TEMPLATES:
                template = ReportTemplate(
                    tenant_id=tenant.id,
                    name=template_data["name"],
                    description=template_data["description"],
                    report_type=template_data["report_type"],
                    default_format=template_data["default_format"],
                    config=template_data["config"],
                    is_active=True,
                    is_system=False,
                    available_formats=["pdf", "csv", "excel"],
                    created_by_user_id=user.id,
                )
                db.add(template)
                print(f"      {template_data['name']}")
            print(f"      Created {len(DEMO_REPORT_TEMPLATES)} report templates")

            print("\n[7/7] Creating activity log...")
            for i, activity in enumerate(DEMO_ACTIVITIES):
                log = AuditLog(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    action=activity["action"],
                    resource_type=activity["resource_type"],
                    resource_id=activity["resource_id"],
                    ip_address="192.168.1.1",
                    user_agent="Demo Seeder",
                    created_at=datetime.now(timezone.utc) - timedelta(hours=i * 2),
                )
                db.add(log)
            print(f"      Created {len(DEMO_ACTIVITIES)} activity entries")

            await db.commit()

            print("\n" + "=" * 60)
            print("Demo data seeded successfully!")
            print("=" * 60)
            print("\nLogin credentials:")
            print("  Email:    demo@stratum.ai")
            print("  Password: demo1234")
            print("\nDashboard metrics summary:")

            total_spend = sum(c["spend_cents"] for c in DEMO_CAMPAIGNS) / 100
            total_revenue = sum(c["revenue_cents"] for c in DEMO_CAMPAIGNS) / 100
            total_conversions = sum(c["conversions"] for c in DEMO_CAMPAIGNS)
            overall_roas = total_revenue / total_spend if total_spend > 0 else 0

            print(f"  Total Spend:       ${total_spend:,.2f}")
            print(f"  Total Revenue:     ${total_revenue:,.2f}")
            print(f"  Overall ROAS:      {overall_roas:.2f}x")
            print(f"  Total Conversions: {total_conversions:,}")
            print(f"  Active Campaigns:  {len([c for c in DEMO_CAMPAIGNS if c['status'] == CampaignStatus.ACTIVE])}")
            print("\n" + "=" * 60)

        except Exception as e:
            await db.rollback()
            print(f"\n[ERROR] Failed to seed data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
