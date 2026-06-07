#!/usr/bin/env python3
"""
Stratum AI - Documentation Pages Seed Script

Loads the 23 built-in documentation articles into the CMS as editable,
published pages (slug ``docs-<slug>``, e.g. ``docs-quickstart``,
``docs-cdp-profiles``). After seeding they appear under /cms/pages and the
public /docs/* routes render the CMS copy (DocArticlePage prefers a published
``docs-*`` page over its built-in content).

The page bodies come from ``scripts/data/docs_seed.json``, which is generated
from the frontend registry (the single source of truth):

    npx tsx frontend/scripts/gen-docs-seed.ts

Usage:
    docker compose exec api python scripts/seed_docs_pages.py
    docker compose exec api python scripts/seed_docs_pages.py --overwrite

By default, existing ``docs-*`` pages are left untouched (so editor changes are
preserved). Pass --overwrite to refresh title/content/meta from the JSON.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.cms import CMSPage, CMSPageStatus

DATA_FILE = Path(__file__).parent / "data" / "docs_seed.json"


async def seed_docs_pages(overwrite: bool) -> None:
    """Upsert the documentation articles as published CMS pages."""
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found. Generate it first with:")
        print("  npx tsx frontend/scripts/gen-docs-seed.ts")
        sys.exit(1)

    pages = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("  Stratum AI - Documentation Pages Seed")
    print("=" * 60)
    print(f"  Source: {DATA_FILE.name} ({len(pages)} articles)")
    print("=" * 60)

    created = updated = skipped = 0

    async with async_session() as db:
        for p in pages:
            slug = p["slug"]
            result = await db.execute(select(CMSPage).where(CMSPage.slug == slug))
            existing = result.scalar_one_or_none()

            if existing is not None:
                if not overwrite:
                    skipped += 1
                    print(f"  · skip   {slug} (exists)")
                    continue
                existing.title = p["title"]
                existing.content = p["content"]
                existing.meta_title = p["meta_title"]
                existing.meta_description = p["meta_description"]
                existing.template = "default"
                existing.status = CMSPageStatus.PUBLISHED.value
                existing.is_deleted = False
                if existing.published_at is None:
                    existing.published_at = datetime.now(timezone.utc)
                updated += 1
                print(f"  ~ update {slug}")
            else:
                db.add(
                    CMSPage(
                        title=p["title"],
                        slug=slug,
                        content=p["content"],
                        content_json=None,
                        status=CMSPageStatus.PUBLISHED.value,
                        published_at=datetime.now(timezone.utc),
                        meta_title=p["meta_title"],
                        meta_description=p["meta_description"],
                        template="default",
                        show_in_navigation=False,
                    )
                )
                created += 1
                print(f"  + create {slug}")

        await db.commit()

    await engine.dispose()

    print("=" * 60)
    print(f"  Done. created={created} updated={updated} skipped={skipped}")
    if skipped and not overwrite:
        print("  (re-run with --overwrite to refresh existing pages)")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed documentation articles as CMS pages")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Refresh existing docs-* pages from the JSON (otherwise they are skipped)",
    )
    args = parser.parse_args()
    asyncio.run(seed_docs_pages(args.overwrite))


if __name__ == "__main__":
    main()
