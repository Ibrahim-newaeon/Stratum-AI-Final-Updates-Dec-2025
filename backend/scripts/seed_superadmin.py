#!/usr/bin/env python3
"""
Stratum AI - Super Admin Seed Script

Creates a super admin user with cross-tenant platform access.
Uses raw SQL to bypass Row-Level Security policies.

Usage:
    docker compose exec api python scripts/seed_superadmin.py

Or from the backend folder:
    python scripts/seed_superadmin.py
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup

# =============================================================================
# Super Admin Configuration
# =============================================================================

SUPERADMIN_EMAIL = "ibrahim@new-aeon.com"
SUPERADMIN_PASSWORD = "Newaeon@2025"
SUPERADMIN_NAME = "Ibrahim (Super Admin)"
SUPERADMIN_TENANT_NAME = "Stratum Platform"
SUPERADMIN_TENANT_SLUG = "stratum-platform"


async def create_superadmin():
    """Create super admin user and platform tenant using raw SQL."""

    # Create async engine
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async with engine.begin() as conn:
        try:
            # Set superadmin context to bypass RLS policies
            await conn.execute(text("SELECT set_tenant_context(1, true)"))

            # Prepare values
            email_hash = hash_pii_for_lookup(SUPERADMIN_EMAIL.lower())
            encrypted_email = encrypt_pii(SUPERADMIN_EMAIL.lower())
            encrypted_name = encrypt_pii(SUPERADMIN_NAME)
            password_hash = get_password_hash(SUPERADMIN_PASSWORD)
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
                print(f"Super admin already exists: {SUPERADMIN_EMAIL}")
                print(f"  User ID: {existing[0]}")
                print(f"  Role: {existing[1]}")
                print(f"  Active: {existing[2]}")
                print(f"  Verified: {existing[3]}")
                return

            # Check/create tenant
            result = await conn.execute(
                text("SELECT id, name FROM tenants WHERE slug = :slug"),
                {"slug": SUPERADMIN_TENANT_SLUG},
            )
            tenant = result.fetchone()

            if not tenant:
                print(f"Creating platform tenant: {SUPERADMIN_TENANT_NAME}")
                result = await conn.execute(
                    text("""
                        INSERT INTO tenants (name, slug, plan, settings, feature_flags, max_users, max_campaigns, created_at, updated_at, is_deleted)
                        VALUES (:name, :slug, 'enterprise', '{}', '{}', 100, 1000, :now, :now, false)
                        RETURNING id
                    """),
                    {"name": SUPERADMIN_TENANT_NAME, "slug": SUPERADMIN_TENANT_SLUG, "now": now},
                )
                tenant_id = result.fetchone()[0]
                print(f"  Tenant ID: {tenant_id}")
            else:
                tenant_id = tenant[0]
                print(f"Using existing tenant: {tenant[1]} (ID: {tenant_id})")

            # Create super admin user using raw SQL
            print(f"\nCreating super admin user: {SUPERADMIN_EMAIL}")

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
                    "password_hash": password_hash,
                    "full_name": encrypted_name,
                    "now": now,
                },
            )
            user_id = result.fetchone()[0]

            print("\n" + "=" * 50)
            print("SUPER ADMIN CREATED SUCCESSFULLY")
            print("=" * 50)
            print(f"  Email:    {SUPERADMIN_EMAIL}")
            print(f"  Password: {SUPERADMIN_PASSWORD}")
            print("  Role:     superadmin")
            print(f"  Tenant:   {SUPERADMIN_TENANT_NAME}")
            print(f"  User ID:  {user_id}")
            print("=" * 50)
            print("\nYou can now log in at /login with these credentials.")

        except Exception as e:
            print(f"\nError creating super admin: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Stratum AI - Super Admin Seed Script")
    print("=" * 50 + "\n")

    asyncio.run(create_superadmin())
