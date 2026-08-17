#!/usr/bin/env python3
"""
Stratum AI - Super Admin Seed Script

Creates a super admin user with cross-tenant platform access.
Uses raw SQL to bypass Row-Level Security policies.

The seeder is *create-only* by default: if the account already exists its
password, active, and verified flags are left alone. Set
``SUPERADMIN_FORCE_RESET=true`` to reset them from ``SUPERADMIN_PASSWORD``
(the credential-recovery path).

Usage:
    docker compose exec api python scripts/seed_superadmin.py

Or from the backend folder:
    python scripts/seed_superadmin.py
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

# Minimum length enforced on SUPERADMIN_PASSWORD.
MIN_PASSWORD_LENGTH = 16

_TRUTHY = {"1", "true", "yes", "on"}


class SuperadminConfigError(RuntimeError):
    """Raised when the superadmin env configuration is present but invalid.

    Deliberately a plain ``RuntimeError`` subclass rather than ``SystemExit``:
    this module is imported by the FastAPI lifespan, and ``SystemExit`` derives
    from ``BaseException``, so it would escape the lifespan's ``except
    Exception`` and abort API startup entirely.
    """


def _env(name: str, default: str = "") -> str:
    """Read an env var, treating empty/whitespace as unset.

    docker-compose passes ``SUPERADMIN_EMAIL=${SUPERADMIN_EMAIL:-}``, so an
    absent key arrives as an empty string rather than being absent.
    """
    return (os.environ.get(name) or "").strip() or default


def load_config() -> dict[str, str] | None:
    """Resolve superadmin settings from the environment.

    Returns ``None`` when the credentials are not configured at all — that is a
    valid state meaning "no superadmin bootstrap requested". Raises
    :class:`SuperadminConfigError` when they are configured but invalid, so a
    typo is loud instead of silently skipped.
    """
    email = _env("SUPERADMIN_EMAIL")
    password = _env("SUPERADMIN_PASSWORD")

    if not email and not password:
        return None

    if not email or not password:
        raise SuperadminConfigError(
            "SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must both be set "
            "(one is missing)."
        )

    if len(password) < MIN_PASSWORD_LENGTH:
        raise SuperadminConfigError(
            f"SUPERADMIN_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    return {
        "email": email,
        "password": password,
        "name": _env("SUPERADMIN_NAME", "Platform Super Admin"),
        "tenant_name": _env("SUPERADMIN_TENANT_NAME", "Stratum Platform"),
        "tenant_slug": _env("SUPERADMIN_TENANT_SLUG", "stratum-platform"),
    }


def force_reset_requested() -> bool:
    """True when SUPERADMIN_FORCE_RESET opts into overwriting an existing account."""
    return _env("SUPERADMIN_FORCE_RESET").lower() in _TRUTHY


async def create_superadmin() -> None:
    """Create the super admin user and platform tenant using raw SQL.

    Idempotent and create-only: an existing account is left untouched unless
    ``SUPERADMIN_FORCE_RESET`` is set. Safe to call on every app startup.
    """
    config = load_config()
    if config is None:
        print(
            "SUPERADMIN_EMAIL/SUPERADMIN_PASSWORD not set - skipping superadmin seed."
        )
        return

    force_reset = force_reset_requested()

    # Create async engine
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    try:
        # Step 1: Add 'superadmin' to userrole enum if missing (requires AUTOCOMMIT)
        # ALTER TYPE ADD VALUE cannot run inside a transaction block
        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            try:
                result = await conn.execute(
                    text(
                        "SELECT 1 FROM pg_enum WHERE enumtypid = 'userrole'::regtype AND enumlabel = 'superadmin'"
                    )
                )
                if not result.fetchone():
                    await conn.execute(
                        text("ALTER TYPE userrole ADD VALUE 'superadmin'")
                    )
                    print("Added 'superadmin' to userrole enum")
            except Exception as e:
                print(f"Note: enum check skipped ({e})")

        # Step 2: Create tenant and user in a transaction
        async with engine.begin() as conn:
            # Set superadmin context to bypass RLS policies (may not exist yet)
            try:
                await conn.execute(text("SELECT set_tenant_context(1, true)"))
            except Exception:
                pass  # RLS function not yet created, that's OK

            # Prepare values
            email_hash = hash_pii_for_lookup(config["email"].lower())
            encrypted_email = encrypt_pii(config["email"].lower())
            encrypted_name = encrypt_pii(config["name"])
            now = datetime.now(UTC)

            # Check if super admin already exists
            result = await conn.execute(
                text(
                    "SELECT id, role, is_active, is_verified FROM users WHERE email_hash = :email_hash"
                ),
                {"email_hash": email_hash},
            )
            existing = result.fetchone()

            if existing:
                if not force_reset:
                    # Create-only. Overwriting here would silently revert any
                    # password change made through the UI on the next restart,
                    # and re-enable a deliberately deactivated account.
                    print(
                        f"Super admin already exists (user ID {existing[0]}) - "
                        "leaving password and flags untouched."
                    )
                    print(
                        "  Set SUPERADMIN_FORCE_RESET=true to reset it from "
                        "SUPERADMIN_PASSWORD."
                    )
                    return

                print(f"Super admin already exists: user ID {existing[0]}")
                print("  SUPERADMIN_FORCE_RESET set - resetting password and flags...")
                await conn.execute(
                    text(
                        "UPDATE users SET password_hash = :password_hash, is_active = true, is_verified = true WHERE email_hash = :email_hash"
                    ),
                    {
                        "password_hash": get_password_hash(config["password"]),
                        "email_hash": email_hash,
                    },
                )
                print("  Password reset successfully!")
                return

            # Check/create tenant
            result = await conn.execute(
                text("SELECT id, name FROM tenants WHERE slug = :slug"),
                {"slug": config["tenant_slug"]},
            )
            tenant = result.fetchone()

            if not tenant:
                print(f"Creating platform tenant: {config['tenant_name']}")
                result = await conn.execute(
                    text("""
                        INSERT INTO tenants (name, slug, plan, settings, feature_flags, max_users, max_campaigns, created_at, updated_at, is_deleted)
                        VALUES (:name, :slug, 'enterprise', '{}', '{}', 100, 1000, :now, :now, false)
                        RETURNING id
                    """),
                    {
                        "name": config["tenant_name"],
                        "slug": config["tenant_slug"],
                        "now": now,
                    },
                )
                tenant_id = result.fetchone()[0]
                print(f"  Tenant ID: {tenant_id}")
            else:
                tenant_id = tenant[0]
                print(f"Using existing tenant: {tenant[1]} (ID: {tenant_id})")

            # Create super admin user using raw SQL
            print(f"\nCreating super admin user: {config['email']}")

            result = await conn.execute(
                text("""
                    INSERT INTO users (
                        tenant_id, email, email_hash, password_hash, full_name,
                        role, permissions, is_active, is_verified,
                        locale, timezone, preferences,
                        consent_marketing, consent_analytics,
                        created_at, updated_at, is_deleted
                    ) VALUES (
                        :tenant_id, :email, :email_hash, :password_hash, :full_name,
                        'superadmin', '{}', true, true,
                        'en', 'UTC', '{}',
                        false, true,
                        :now, :now, false
                    )
                    RETURNING id
                """),
                {
                    "tenant_id": tenant_id,
                    "email": encrypted_email,
                    "email_hash": email_hash,
                    "password_hash": get_password_hash(config["password"]),
                    "full_name": encrypted_name,
                    "now": now,
                },
            )
            user_id = result.fetchone()[0]

            print("\n" + "=" * 50)
            print("SUPER ADMIN CREATED SUCCESSFULLY")
            print("=" * 50)
            print(f"  Email:    {config['email']}")
            print("  Password:  [set via SUPERADMIN_PASSWORD env var]")
            print("  Role:     superadmin")
            print(f"  Tenant:   {config['tenant_name']}")
            print(f"  User ID:  {user_id}")
            print("=" * 50)
            print("\nYou can now log in at /login with these credentials.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Stratum AI - Super Admin Seed Script")
    print("=" * 50 + "\n")

    # Run as a CLI, missing configuration is a usage error rather than a
    # no-op — the operator explicitly asked for a seed.
    if load_config() is None:
        print(
            "ERROR: SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD environment variables are required."
        )
        print(
            "Example: SUPERADMIN_EMAIL=admin@example.com "
            "SUPERADMIN_PASSWORD=$(openssl rand -base64 32) python scripts/seed_superadmin.py"
        )
        sys.exit(1)

    try:
        asyncio.run(create_superadmin())
    except SuperadminConfigError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nError creating super admin: {exc}")
        raise
