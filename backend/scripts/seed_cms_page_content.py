#!/usr/bin/env python3
"""
Stratum AI - CMS Page Content Population Script

Populates CMS pages (Features, Pricing) with their existing hardcoded content
and creates FAQ posts from the hardcoded FAQ data, so everything is editable
through the CMS dashboard.

Prerequisites: Run seed_cms_content.py first to create categories and pages.

Usage:
    python scripts/seed_cms_page_content.py
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# =============================================================================
# Features page content_json (matches FeaturesPageContent type)
# =============================================================================

FEATURES_CONTENT = {
    "features": [
        {
            "iconName": "ShieldCheckIcon",
            "title": "Trust-Gated Autopilot",
            "description": "Automations only execute when signal health passes safety thresholds. No more blind optimization.",
            "color": "#a855f7",
        },
        {
            "iconName": "SignalIcon",
            "title": "Signal Health Monitoring",
            "description": "Real-time monitoring of data quality across all connected platforms with instant anomaly detection.",
            "color": "#06b6d4",
        },
        {
            "iconName": "UserGroupIcon",
            "title": "Customer Data Platform",
            "description": "Unified customer profiles with identity resolution, behavioral segmentation, and lifecycle tracking.",
            "color": "#f97316",
        },
        {
            "iconName": "ArrowPathIcon",
            "title": "Multi-Platform Audience Sync",
            "description": "Push segments to Meta, Google, TikTok & Snapchat with one click. Auto-sync keeps audiences fresh.",
            "color": "#34c759",
        },
        {
            "iconName": "ChartBarIcon",
            "title": "Advanced Attribution",
            "description": "Multi-touch attribution models with conversion path analysis and incrementality testing.",
            "color": "#3b82f6",
        },
        {
            "iconName": "CpuChipIcon",
            "title": "ML-Powered Predictions",
            "description": "Churn prediction, LTV forecasting, and next-best-action recommendations powered by machine learning.",
            "color": "#ec4899",
        },
        {
            "iconName": "BoltIcon",
            "title": "Real-Time Event Processing",
            "description": "Process millions of events per second with sub-second latency for instant personalization.",
            "color": "#eab308",
        },
        {
            "iconName": "ChartPieIcon",
            "title": "RFM Analysis",
            "description": "Built-in Recency, Frequency, Monetary analysis for customer value segmentation.",
            "color": "#00c7be",
        },
        {
            "iconName": "CloudArrowUpIcon",
            "title": "Flexible Data Export",
            "description": "Export audiences as CSV or JSON with custom traits, events, and computed attributes.",
            "color": "#8b5cf6",
        },
        {
            "iconName": "DocumentChartBarIcon",
            "title": "Custom Reporting",
            "description": "Build custom reports and dashboards with drag-and-drop widgets and scheduled exports.",
            "color": "#f43f5e",
        },
        {
            "iconName": "CubeTransparentIcon",
            "title": "Identity Graph",
            "description": "Visual identity resolution showing cross-device connections and merge history.",
            "color": "#06b6d4",
        },
        {
            "iconName": "SparklesIcon",
            "title": "AI Campaign Optimization",
            "description": "Automatic bid adjustments, budget allocation, and creative rotation based on performance.",
            "color": "#a855f7",
        },
    ]
}

# =============================================================================
# Pricing page content_json (matches PricingPageContent type)
# =============================================================================

PRICING_CONTENT = {
    "tiers": [
        {
            "name": "Starter",
            "price": "$499",
            "period": "/month",
            "description": "Perfect for growing teams getting started with revenue intelligence.",
            "features": [
                "Up to 100K monthly events",
                "5 team members",
                "3 ad platform connections",
                "Basic signal health monitoring",
                "Standard attribution models",
                "Email support",
            ],
            "cta": "Start Free Trial",
            "highlighted": False,
        },
        {
            "name": "Professional",
            "price": "$1,499",
            "period": "/month",
            "description": "For scaling teams that need advanced automation and insights.",
            "features": [
                "Up to 1M monthly events",
                "15 team members",
                "Unlimited platform connections",
                "Advanced signal health + alerts",
                "Trust-Gated Autopilot",
                "CDP with audience sync",
                "Custom attribution models",
                "ML predictions & forecasting",
                "Priority support",
            ],
            "cta": "Start Free Trial",
            "highlighted": True,
        },
        {
            "name": "Enterprise",
            "price": "Custom",
            "period": "",
            "description": "For large organizations with complex requirements.",
            "features": [
                "Unlimited events",
                "Unlimited team members",
                "All Professional features",
                "Custom integrations",
                "Dedicated account manager",
                "SLA guarantee",
                "On-premise deployment option",
                "Advanced security & compliance",
                "Custom training & onboarding",
            ],
            "cta": "Contact Sales",
            "highlighted": False,
        },
    ],
    "faqs": [
        {
            "question": "What counts as a monthly event?",
            "answer": "Events include any data point tracked through our platform: page views, purchases, form submissions, API calls, and more.",
        },
        {
            "question": "Can I change plans later?",
            "answer": "Yes, you can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.",
        },
        {
            "question": "Is there a free trial?",
            "answer": "Yes, all plans include a 14-day free trial with full access to all features. No credit card required.",
        },
        {
            "question": "What payment methods do you accept?",
            "answer": "We accept all major credit cards, ACH transfers, and wire transfers for annual Enterprise plans.",
        },
    ],
}

# =============================================================================
# FAQ items (stored as CMS posts in landing-faq category)
# =============================================================================

FAQ_ITEMS = [
    # Pricing & Plans
    {
        "title": "What pricing plans does Stratum AI offer?",
        "content": "We offer three tiers: Starter ($499/mo) for growing teams, Professional ($1,499/mo) for scaling businesses with advanced automation, and custom Enterprise plans for large organizations. Each tier includes a 14-day free trial with full feature access.",
        "faq_category": "pricing",
        "display_order": 1,
    },
    {
        "title": "Is there a free trial available?",
        "content": "Yes! We offer a 14-day free trial on all plans with full feature access. No credit card required to start. You can also use our Interactive Demo Mode to explore the platform with sample data before signing up.",
        "faq_category": "pricing",
        "display_order": 2,
    },
    {
        "title": "Can I change my plan later?",
        "content": "Absolutely. You can upgrade or downgrade your plan at any time. Upgrades take effect immediately with prorated billing. Downgrades take effect at the start of your next billing cycle.",
        "faq_category": "pricing",
        "display_order": 3,
    },
    # Features
    {
        "title": "What is the Trust-Gated Autopilot?",
        "content": "Trust-Gated Autopilot is our core innovation. It automatically executes optimizations ONLY when signal health passes safety thresholds (70+ score). This prevents costly mistakes from bad data while maximizing automation when conditions are right.",
        "faq_category": "features",
        "display_order": 4,
    },
    {
        "title": "Which ad platforms do you support?",
        "content": "We support Meta (Facebook/Instagram), Google Ads, TikTok Ads, and Snapchat Ads. Our platform connects via OAuth for campaign management and CAPI for server-side conversion tracking.",
        "faq_category": "features",
        "display_order": 5,
    },
    {
        "title": "What is the CDP and how does it work?",
        "content": "Our Customer Data Platform (CDP) unifies customer profiles across all touchpoints. It includes identity resolution, behavioral segmentation, RFM analysis, and one-click audience sync to all major ad platforms.",
        "faq_category": "features",
        "display_order": 6,
    },
    # Trust Engine
    {
        "title": "How does Signal Health scoring work?",
        "content": "Signal Health is a 0-100 score measuring data reliability. It factors in data freshness, completeness, consistency, and anomaly detection. Scores above 70 are 'Healthy' (green), 40-70 are 'Degraded' (yellow), and below 40 are 'Unhealthy' (red).",
        "faq_category": "trust-engine",
        "display_order": 7,
    },
    {
        "title": "What happens when Signal Health drops?",
        "content": "When Signal Health drops below thresholds, the Trust Gate automatically blocks automated actions and alerts your team. This prevents optimizations based on unreliable data. You can still take manual actions with an override.",
        "faq_category": "trust-engine",
        "display_order": 8,
    },
    {
        "title": "Can I customize Trust Gate thresholds?",
        "content": "Yes, on Growth plans and above. You can set custom thresholds per campaign, automation rule, or globally. Enterprise plans include advanced configuration with time-based rules and multi-signal gates.",
        "faq_category": "trust-engine",
        "display_order": 9,
    },
    # Integrations
    {
        "title": "How do I connect my ad accounts?",
        "content": "Go to Tenant Settings > Connect Platforms. Click 'Connect' on any platform to start the OAuth flow. You'll be redirected to the platform to grant permissions, then automatically returned to Stratum AI.",
        "faq_category": "integrations",
        "display_order": 10,
    },
    {
        "title": "What is CAPI and do I need it?",
        "content": "CAPI (Conversions API) sends conversion events server-side directly to ad platforms. This bypasses browser limitations like ad blockers and iOS privacy restrictions. It improves match rates from ~42% to 70-90%, significantly boosting ROAS.",
        "faq_category": "integrations",
        "display_order": 11,
    },
    {
        "title": "Do you integrate with Slack?",
        "content": "Yes! Our Slack integration sends real-time Trust Gate alerts, daily performance summaries, and anomaly notifications to your chosen channels. Configure it in Settings > Integrations.",
        "faq_category": "integrations",
        "display_order": 12,
    },
    # Data & Privacy
    {
        "title": "How do you handle my data?",
        "content": "We follow strict data security practices: SOC 2 Type II compliant, AES-256 encryption at rest, TLS 1.3 in transit. We never sell your data or use it for anything other than providing our service to you.",
        "faq_category": "data",
        "display_order": 13,
    },
    {
        "title": "Are you GDPR and CCPA compliant?",
        "content": "Yes. We're fully GDPR and CCPA compliant. Our CDP includes built-in consent management, data subject request handling, and automatic PII hashing for platform syncs. DPA available for all customers.",
        "faq_category": "data",
        "display_order": 14,
    },
    {
        "title": "Where is my data stored?",
        "content": "Data is stored in AWS data centers. US customers use us-east-1, EU customers use eu-west-1. Enterprise plans can specify custom regions. All data is encrypted and backed up with 99.9% SLA.",
        "faq_category": "data",
        "display_order": 15,
    },
    # Support
    {
        "title": "What support options are available?",
        "content": "Starter: Email support (48h response). Growth: Priority email + chat (24h response). Scale: Dedicated CSM + phone support (4h response). Enterprise: 24/7 support + SLA guarantees.",
        "faq_category": "support",
        "display_order": 16,
    },
    {
        "title": "Do you offer onboarding assistance?",
        "content": "Yes! All plans include self-service onboarding with interactive guides. Growth and above get a 1-hour kickoff call. Scale and Enterprise receive full white-glove onboarding with dedicated implementation support.",
        "faq_category": "support",
        "display_order": 17,
    },
    {
        "title": "How can I contact the team?",
        "content": "Email us at support@stratum.ai for support, sales@stratum.ai for sales inquiries, or use the in-app chat. Enterprise customers have direct Slack channels with our team.",
        "faq_category": "support",
        "display_order": 18,
    },
]


def slugify(text: str) -> str:
    """Simple slug generation."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


async def populate_cms():
    """Populate CMS pages with content and create FAQ posts."""

    db_url = settings.database_url
    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        try:
            now = datetime.now(UTC)

            # =====================================================
            # Step 1: Update Features page content_json
            # =====================================================
            print("\n[1/3] Updating Features page content...")
            result = await conn.execute(
                text("SELECT id, content_json FROM cms_pages WHERE slug = 'features'")
            )
            row = result.fetchone()
            if row:
                features_json = json.dumps(FEATURES_CONTENT)
                await conn.execute(
                    text("UPDATE cms_pages SET content_json = :cj, updated_at = :now WHERE slug = 'features'"),
                    {"cj": features_json, "now": now},
                )
                print("  + Features page updated with 12 feature cards")
            else:
                print("  ! Features page not found - run seed_cms_content.py first")

            # =====================================================
            # Step 2: Update Pricing page content_json
            # =====================================================
            print("\n[2/3] Updating Pricing page content...")
            result = await conn.execute(
                text("SELECT id, content_json FROM cms_pages WHERE slug = 'pricing'")
            )
            row = result.fetchone()
            if row:
                pricing_json = json.dumps(PRICING_CONTENT)
                await conn.execute(
                    text("UPDATE cms_pages SET content_json = :cj, updated_at = :now WHERE slug = 'pricing'"),
                    {"cj": pricing_json, "now": now},
                )
                print("  + Pricing page updated with 3 tiers and 4 FAQs")
            else:
                print("  ! Pricing page not found - run seed_cms_content.py first")

            # =====================================================
            # Step 3: Create FAQ posts in landing-faq category
            # =====================================================
            print("\n[3/3] Creating FAQ posts...")

            # Get landing-faq category ID
            result = await conn.execute(
                text("SELECT id FROM cms_categories WHERE slug = 'landing-faq'")
            )
            cat_row = result.fetchone()
            if not cat_row:
                print("  ! landing-faq category not found - run seed_cms_content.py first")
            else:
                category_id = cat_row[0]
                faqs_created = 0
                faqs_skipped = 0

                for faq in FAQ_ITEMS:
                    slug = slugify(faq["title"])

                    # Check if already exists
                    result = await conn.execute(
                        text("SELECT id FROM cms_posts WHERE slug = :slug"),
                        {"slug": slug},
                    )
                    if result.fetchone():
                        faqs_skipped += 1
                        continue

                    post_id = str(uuid4())
                    # Store faq metadata in meta_title as JSON (the convention used by CMS landing editors)
                    meta_json = json.dumps({
                        "faqCategory": faq["faq_category"],
                        "displayOrder": faq["display_order"],
                    })

                    await conn.execute(
                        text("""
                            INSERT INTO cms_posts (
                                id, title, slug, content, excerpt,
                                status, content_type, meta_title, meta_description,
                                category_id, author_id,
                                is_featured, view_count, version,
                                created_at, updated_at, published_at, is_deleted
                            ) VALUES (
                                :id, :title, :slug, :content, :excerpt,
                                'published', 'article', :meta_title, '',
                                :category_id, NULL,
                                false, 0, 1,
                                :now, :now, :now, false
                            )
                        """),
                        {
                            "id": post_id,
                            "title": faq["title"],
                            "slug": slug,
                            "content": faq["content"],
                            "excerpt": faq["content"][:200],
                            "meta_title": meta_json,
                            "category_id": category_id,
                            "now": now,
                        },
                    )
                    faqs_created += 1

                print(f"  + Created {faqs_created} FAQ posts, {faqs_skipped} already existed")

            # =====================================================
            # Summary
            # =====================================================
            print("\n" + "=" * 60)
            print("  CMS Content Populated Successfully!")
            print("=" * 60)
            print("\n  What's now editable from the CMS dashboard:")
            print("    - Features page: 12 feature cards (CMS > Pages > Features)")
            print("    - Pricing page: 3 tiers + 4 FAQs (CMS > Pages > Pricing)")
            print("    - FAQ page: 18 FAQ items (CMS > Landing Content > FAQ)")
            print("\n  Edit any content in the CMS and the public pages will update.")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[ERROR] Failed to populate CMS content: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Stratum AI - CMS Content Population Script")
    print("=" * 60)
    asyncio.run(populate_cms())
