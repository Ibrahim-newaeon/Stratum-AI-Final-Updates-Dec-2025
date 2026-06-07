#!/usr/bin/env python3
"""
Stratum AI - Marketing Pages Seed Script

Loads the public marketing pages' built-in content into the CMS as editable,
published pages so they appear under /cms/pages and the public pages render the
CMS copy (each page already prefers CMS content over its hardcoded fallback).

Covers 20 pages:
  - 16 structured pages (content_json): features, pricing, integrations,
    api-docs, about, careers, case-studies, changelog, compare, glossary,
    resources, status, and the four solutions-* pages.
  - 4 legal pages (HTML content): privacy, terms, security, dpa.

Page bodies come from ``scripts/data/marketing_seed.json``, generated from the
frontend (single source of truth):

    npx tsx frontend/scripts/gen-marketing-seed.ts

Usage:
    docker compose exec api python scripts/seed_marketing_pages.py
    docker compose exec api python scripts/seed_marketing_pages.py --overwrite

By default, existing pages are left untouched (editor changes preserved). Pass
--overwrite to refresh title/content/content_json/meta from the JSON.
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

DATA_FILE = Path(__file__).parent / "data" / "marketing_seed.json"


async def seed_marketing_pages(overwrite: bool) -> None:
    """Upsert the marketing pages as published CMS pages."""
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found. Generate it first with:")
        print("  npx tsx frontend/scripts/gen-marketing-seed.ts")
        sys.exit(1)

    pages = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("  Stratum AI - Marketing Pages Seed")
    print("=" * 60)
    print(f"  Source: {DATA_FILE.name} ({len(pages)} pages)")
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
                existing.content = p.get("content")
                existing.content_json = p.get("content_json")
                existing.meta_title = p["meta_title"]
                existing.meta_description = p["meta_description"]
                existing.template = p["template"]
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
                        content=p.get("content"),
                        content_json=p.get("content_json"),
                        status=CMSPageStatus.PUBLISHED.value,
                        published_at=datetime.now(timezone.utc),
                        meta_title=p["meta_title"],
                        meta_description=p["meta_description"],
                        template=p["template"],
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
    parser = argparse.ArgumentParser(description="Seed marketing pages as CMS pages")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Refresh existing pages from the JSON (otherwise they are skipped)",
    )
    args = parser.parse_args()
    asyncio.run(seed_marketing_pages(args.overwrite))


if __name__ == "__main__":
    main()
