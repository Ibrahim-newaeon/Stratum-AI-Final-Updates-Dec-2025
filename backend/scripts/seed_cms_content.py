#!/usr/bin/env python3
"""
Stratum AI - CMS Content Seed Script

Seeds essential CMS categories so the Landing Content editors
(Features, FAQ, Pricing) can function, and creates initial CMS pages
with matching slugs for the public website.

Usage:
    docker compose exec api python scripts/seed_cms_content.py

Or from the backend folder:
    python scripts/seed_cms_content.py
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# =============================================================================
# Categories to seed — these are required for the CMS landing content editors
# =============================================================================

CATEGORIES = [
    {
        "name": "Landing Features",
        "slug": "landing-features",
        "description": "Feature items displayed on the landing/home page feature tabs",
        "color": "#8B5CF6",
        "icon": "sparkles",
        "display_order": 1,
    },
    {
        "name": "Landing FAQ",
        "slug": "landing-faq",
        "description": "FAQ items displayed on the landing page FAQ section",
        "color": "#06B6D4",
        "icon": "question-mark-circle",
        "display_order": 2,
    },
    {
        "name": "Landing Pricing",
        "slug": "landing-pricing",
        "description": "Pricing tiers displayed on the landing page pricing section",
        "color": "#F59E0B",
        "icon": "currency-dollar",
        "display_order": 3,
    },
    {
        "name": "Blog",
        "slug": "blog",
        "description": "General blog posts",
        "color": "#10B981",
        "icon": "document-text",
        "display_order": 4,
    },
    {
        "name": "Engineering",
        "slug": "engineering",
        "description": "Technical and engineering blog posts",
        "color": "#3B82F6",
        "icon": "code-bracket",
        "display_order": 5,
    },
    {
        "name": "Product Updates",
        "slug": "product-updates",
        "description": "Product announcements and updates",
        "color": "#EC4899",
        "icon": "megaphone",
        "display_order": 6,
    },
    {
        "name": "Company News",
        "slug": "company-news",
        "description": "Company announcements and news",
        "color": "#6366F1",
        "icon": "newspaper",
        "display_order": 7,
    },
]

# =============================================================================
# Pages to seed — these match the slugs used by public website pages
# =============================================================================

PAGES = [
    {
        "title": "Features",
        "slug": "features",
        "template": "features",
        "meta_title": "Stratum AI Features - Trust-Gated Revenue Automation",
        "meta_description": "Explore Stratum AI's powerful features including Trust Engine, CDP, Autopilot, and more.",
        "status": "published",
        "show_in_navigation": True,
        "navigation_label": "Features",
        "navigation_order": 1,
    },
    {
        "title": "Pricing",
        "slug": "pricing",
        "template": "pricing",
        "meta_title": "Stratum AI Pricing - Plans for Every Business",
        "meta_description": "Choose the right Stratum AI plan for your business. Starter, Professional, and Enterprise tiers available.",
        "status": "published",
        "show_in_navigation": True,
        "navigation_label": "Pricing",
        "navigation_order": 2,
    },
    {
        "title": "Integrations",
        "slug": "integrations",
        "template": "integrations",
        "meta_title": "Stratum AI Integrations - Connect Your Marketing Stack",
        "meta_description": "Connect Stratum AI with Google Ads, Meta, TikTok, Snapchat, HubSpot, and more.",
        "status": "published",
        "show_in_navigation": True,
        "navigation_label": "Integrations",
        "navigation_order": 3,
    },
    {
        "title": "About",
        "slug": "about",
        "template": "about",
        "meta_title": "About Stratum AI - Our Mission and Team",
        "meta_description": "Learn about Stratum AI's mission to bring trust-gated automation to revenue operations.",
        "status": "published",
        "show_in_navigation": True,
        "navigation_label": "About",
        "navigation_order": 4,
    },
    {
        "title": "Changelog",
        "slug": "changelog",
        "template": "changelog",
        "meta_title": "Stratum AI Changelog - Product Updates",
        "meta_description": "See what's new in Stratum AI. Latest features, improvements, and fixes.",
        "status": "published",
        "show_in_navigation": False,
        "navigation_label": "Changelog",
        "navigation_order": 10,
    },
]


async def seed_cms_content():
    """Seed CMS categories and pages using raw SQL."""

    db_url = settings.database_url
    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        try:
            # --- Seed Categories ---
            print("\n[1/2] Seeding CMS categories...")
            now = datetime.now(UTC)
            categories_created = 0
            categories_skipped = 0

            for cat in CATEGORIES:
                # Check if category slug already exists
                result = await conn.execute(
                    text("SELECT id FROM cms_categories WHERE slug = :slug"),
                    {"slug": cat["slug"]},
                )
                existing = result.fetchone()

                if existing:
                    print(f"  ✓ Category '{cat['name']}' already exists (skipped)")
                    categories_skipped += 1
                    continue

                cat_id = str(uuid4())
                await conn.execute(
                    text("""
                        INSERT INTO cms_categories (id, name, slug, description, color, icon, display_order, is_active, created_at, updated_at)
                        VALUES (:id, :name, :slug, :description, :color, :icon, :display_order, true, :now, :now)
                    """),
                    {
                        "id": cat_id,
                        "name": cat["name"],
                        "slug": cat["slug"],
                        "description": cat["description"],
                        "color": cat["color"],
                        "icon": cat["icon"],
                        "display_order": cat["display_order"],
                        "now": now,
                    },
                )
                print(f"  + Created category: {cat['name']} ({cat['slug']})")
                categories_created += 1

            print(f"\n  Categories: {categories_created} created, {categories_skipped} already existed")

            # --- Seed Pages ---
            print("\n[2/2] Seeding CMS pages...")
            pages_created = 0
            pages_skipped = 0

            for page in PAGES:
                # Check if page slug already exists
                result = await conn.execute(
                    text("SELECT id FROM cms_pages WHERE slug = :slug"),
                    {"slug": page["slug"]},
                )
                existing = result.fetchone()

                if existing:
                    print(f"  ✓ Page '{page['title']}' already exists (skipped)")
                    pages_skipped += 1
                    continue

                page_id = str(uuid4())
                published_at = now if page["status"] == "published" else None

                await conn.execute(
                    text("""
                        INSERT INTO cms_pages (
                            id, title, slug, content, content_json, template, status,
                            meta_title, meta_description,
                            show_in_navigation, navigation_label, navigation_order,
                            published_at, created_at, updated_at, is_deleted
                        )
                        VALUES (
                            :id, :title, :slug, '', '{}', :template, :status,
                            :meta_title, :meta_description,
                            :show_in_navigation, :navigation_label, :navigation_order,
                            :published_at, :now, :now, false
                        )
                    """),
                    {
                        "id": page_id,
                        "title": page["title"],
                        "slug": page["slug"],
                        "template": page["template"],
                        "status": page["status"],
                        "meta_title": page["meta_title"],
                        "meta_description": page["meta_description"],
                        "show_in_navigation": page["show_in_navigation"],
                        "navigation_label": page["navigation_label"],
                        "navigation_order": page["navigation_order"],
                        "published_at": published_at,
                        "now": now,
                    },
                )
                print(f"  + Created page: {page['title']} (/{page['slug']})")
                pages_created += 1

            print(f"\n  Pages: {pages_created} created, {pages_skipped} already existed")

            print("\n" + "=" * 60)
            print("  CMS Content Seeded Successfully!")
            print("=" * 60)
            print("\n  You can now:")
            print("    1. Go to CMS Dashboard > Landing Content > Features")
            print("       to add feature items for the landing page")
            print("    2. Go to Landing Content > FAQ to add FAQ items")
            print("    3. Go to Landing Content > Pricing to add pricing tiers")
            print("    4. Go to Pages to edit the page templates (Features, Pricing, etc.)")
            print("    5. Go to Posts to create blog posts in the Blog category")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[ERROR] Failed to seed CMS content: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Stratum AI - CMS Content Seed Script")
    print("=" * 60)

    asyncio.run(seed_cms_content())
