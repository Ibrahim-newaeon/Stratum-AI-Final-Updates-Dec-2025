#!/usr/bin/env python3
"""Quick verification of CMS seeded data."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def verify():
    db_url = settings.database_url
    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)

    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT name, slug FROM cms_categories ORDER BY display_order"))
        cats = r.fetchall()
        print(f"Categories ({len(cats)}):")
        for c in cats:
            print(f"  - {c[0]} ({c[1]})")

        r = await conn.execute(text("SELECT title, slug, status, template FROM cms_pages ORDER BY navigation_order"))
        pages = r.fetchall()
        print(f"\nPages ({len(pages)}):")
        for p in pages:
            print(f"  - {p[0]} (/{p[1]}) [{p[2]}] template={p[3]}")

        # Check content_json is populated
        r = await conn.execute(text("SELECT slug, content_json FROM cms_pages WHERE slug IN ('features', 'pricing')"))
        for row in r.fetchall():
            cj = row[1]
            if isinstance(cj, str):
                cj = json.loads(cj)
            if cj and cj != {}:
                keys = list(cj.keys())
                print(f"\n  Page '{row[0]}' content_json keys: {keys}")
                if "features" in cj:
                    print(f"    -> {len(cj['features'])} features")
                if "tiers" in cj:
                    print(f"    -> {len(cj['tiers'])} pricing tiers")
                if "faqs" in cj:
                    print(f"    -> {len(cj['faqs'])} pricing FAQs")
            else:
                print(f"\n  Page '{row[0]}' content_json is EMPTY")

        # Check FAQ posts
        r = await conn.execute(text("""
            SELECT COUNT(*) FROM cms_posts p
            JOIN cms_categories c ON p.category_id = c.id
            WHERE c.slug = 'landing-faq' AND p.is_deleted = false
        """))
        faq_count = r.scalar()
        print(f"\nFAQ Posts: {faq_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
