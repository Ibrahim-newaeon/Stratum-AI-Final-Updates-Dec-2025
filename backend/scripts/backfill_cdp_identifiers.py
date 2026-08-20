#!/usr/bin/env python
# =============================================================================
# Stratum AI - CDP identifier encryption backfill [CDP-04]
# =============================================================================
"""Encrypt the plaintext identifiers migration 064 deliberately left behind.

Migration 064 widened ``cdp_profile_identifiers.identifier_value`` so new
writes could hold ciphertext, and said in its own docstring that converting the
existing rows "needs a deliberate backfill that reads each row, calls
set_identifier_value, and commits per tenant". This is that script.

Usage::

    docker compose exec api python scripts/backfill_cdp_identifiers.py --all-tenants --dry-run
    docker compose exec api python scripts/backfill_cdp_identifiers.py --all-tenants
    docker compose exec api python scripts/backfill_cdp_identifiers.py --tenant 3 --tenant 7

Run the dry pass first. This rewrites PII in place and keeps no plaintext copy;
the only route back is the nightly dump.

Safe to interrupt and re-run: every batch commits, and a row that already
decrypts is left alone, so a second run resumes rather than double-encrypting.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.base_models import Tenant  # noqa: E402
from app.core.pii_keys import get_cached_dek, load_all_tenant_deks  # noqa: E402
from app.core.security import decrypt_pii  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.cdp import CDPProfileIdentifier  # noqa: E402

logger = logging.getLogger("backfill_cdp_identifiers")

DEFAULT_BATCH_SIZE = 500


class MissingTenantDEK(RuntimeError):
    """Raised when a tenant has no data-encryption key in the cache.

    Not a warning and not a skip. ``encrypt_pii`` falls back to the legacy
    global-derived key when the cache misses, and returns successfully -- so
    proceeding would write every such tenant's identifiers under one shared
    key while reporting a clean run, and the dual-read in ``decrypt_pii`` would
    keep the plaintext readable so nothing downstream would notice. Refusing
    is the only outcome that cannot silently produce the wrong thing.
    """


@dataclass
class TenantStats:
    """Row disposition for one tenant."""

    scanned: int = 0
    encrypted: int = 0
    already_encrypted: int = 0
    empty: int = 0


def _is_plaintext(stored: str, tenant_id: int) -> bool:
    """True when ``stored`` is not ciphertext this tenant can read.

    ``decrypt_pii`` dual-reads (tenant DEK, then the legacy global key), so a
    success means the row is already encrypted under one of them and must be
    left alone. Encrypting it again is not detectable by reading the column
    back: it would decrypt to ciphertext instead of to an email address.
    """
    try:
        decrypt_pii(stored, tenant_id)
    except ValueError:
        return True
    return False


async def backfill_tenant(
    session: AsyncSession,
    tenant_id: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> TenantStats:
    """Encrypt every plaintext identifier belonging to ``tenant_id``.

    With ``dry_run`` the rows are classified and counted but never modified or
    committed -- this rewrites production PII and keeps no plaintext copy, so
    the count comes first.
    """
    if get_cached_dek(tenant_id) is None:
        raise MissingTenantDEK(
            f"tenant {tenant_id} has no cached DEK -- run initialize_pii_keys "
            "or ensure_tenant_dek first; refusing to encrypt under the "
            "legacy global key"
        )

    stats = TenantStats()
    last_id = None

    while True:
        statement = (
            select(CDPProfileIdentifier)
            .where(CDPProfileIdentifier.tenant_id == tenant_id)
            .order_by(CDPProfileIdentifier.id)
            .limit(batch_size)
        )
        if last_id is not None:
            statement = statement.where(CDPProfileIdentifier.id > last_id)

        page = (await session.execute(statement)).scalars().all()
        if not page:
            break

        for row in page:
            stats.scanned += 1
            last_id = row.id
            # The model uses the legacy ``Column(...)`` style rather than
            # ``Mapped[...]``, so mypy types the attribute as Column[str]
            # while the instance actually holds the value.
            stored = cast(Optional[str], row._identifier_value_encrypted)

            if not stored:
                stats.empty += 1
            elif _is_plaintext(stored, tenant_id):
                if not dry_run:
                    row.set_identifier_value(stored)
                stats.encrypted += 1
            else:
                stats.already_encrypted += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

        if len(page) < batch_size:
            break

    return stats


# =============================================================================
# Tenant selection
# =============================================================================
async def resolve_tenant_ids(
    session: AsyncSession, requested: Optional[list[int]] = None
) -> list[int]:
    """Return the tenant ids to backfill, verified to exist.

    A requested id that is absent or soft-deleted is dropped with a warning
    rather than silently backfilling nothing under it -- a typo'd id would
    otherwise produce a clean run of all zeros.
    """
    query = select(Tenant.id).where(Tenant.is_deleted.is_(False))
    if requested:
        query = query.where(Tenant.id.in_(requested))

    result = await session.execute(query.order_by(Tenant.id.asc()))
    found = list(result.scalars().all())

    if requested:
        missing = sorted(set(requested) - set(found))
        if missing:
            logger.warning(
                "skipping %d unknown or deleted tenant(s): %s",
                len(missing),
                ", ".join(str(t) for t in missing),
            )
    return found


# =============================================================================
# Reporting
# =============================================================================
def render_table(results: dict[int, Optional[TenantStats]]) -> str:
    header = (
        f"{'tenant':>8}  {'scanned':>9}  {'encrypted':>10}  "
        f"{'already':>9}  {'empty':>7}"
    )
    lines = [header, "-" * len(header)]
    for tenant_id, stats in sorted(results.items()):
        if stats is None:
            lines.append(f"{tenant_id:>8}  {'FAILED':>9}")
            continue
        lines.append(
            f"{tenant_id:>8}  {stats.scanned:>9}  {stats.encrypted:>10}  "
            f"{stats.already_encrypted:>9}  {stats.empty:>7}"
        )
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--tenant",
        dest="tenants",
        type=int,
        action="append",
        help="tenant id to backfill; repeatable",
    )
    target.add_argument(
        "--all-tenants",
        action="store_true",
        help="backfill every tenant that is not soft-deleted",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"rows per commit (default {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="count what would be encrypted without writing",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        # Before anything else. This process is not the API, so its DEK cache
        # starts empty, and encrypt_pii falls back to the legacy global key on
        # a miss without raising. backfill_tenant refuses in that state; this
        # warm-up is what makes that refusal a guard rather than a wall.
        loaded = await load_all_tenant_deks(session)
        logger.info("loaded %d tenant DEK(s)", loaded)

        tenant_ids = await resolve_tenant_ids(session, getattr(args, "tenants", None))
        if not tenant_ids:
            logger.error("no tenants to backfill")
            return 1

        results: dict[int, Optional[TenantStats]] = {}
        for tenant_id in tenant_ids:
            started = time.monotonic()
            try:
                stats = await backfill_tenant(
                    session,
                    tenant_id,
                    batch_size=args.batch_size,
                    dry_run=args.dry_run,
                )
                results[tenant_id] = stats
                logger.info(
                    "tenant %s: %d of %d rows encrypted in %.1fs",
                    tenant_id,
                    stats.encrypted,
                    stats.scanned,
                    time.monotonic() - started,
                )
            except MissingTenantDEK:
                # Never downgrade this to a skip. A tenant with no DEK means a
                # broken key store, and every other tenant in the run shares it.
                logger.exception("tenant %s has no DEK -- aborting the run", tenant_id)
                await session.rollback()
                return 2
            except Exception:
                # One tenant's bad row must not abandon the rest. Batches that
                # already committed stay committed; the session is rolled back
                # to a usable state for the next tenant.
                logger.exception("tenant %s failed", tenant_id)
                await session.rollback()
                results[tenant_id] = None

    print(render_table(results))

    failed = [t for t, stats in results.items() if stats is None]
    encrypted = sum(s.encrypted for s in results.values() if s is not None)

    if args.dry_run:
        print(f"\nDRY RUN -- nothing written. {encrypted} row(s) would be encrypted.")
        return 0

    print(f"\n{encrypted} row(s) encrypted across {len(results)} tenant(s).")
    if failed:
        print(f"{len(failed)} tenant(s) failed: {', '.join(str(t) for t in failed)}")
    return 1 if failed else 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    return asyncio.run(run(build_parser().parse_args()))


if __name__ == "__main__":
    sys.exit(main())
