#!/usr/bin/env python3
"""
Stratum AI - CMS Root Admin Seed Script

Creates a protected root admin account for the CMS.
This account cannot be deleted or demoted by other admins.

Usage:
    docker compose exec api python scripts/seed_cms_admin.py

    Or with custom credentials:
    docker compose exec api python scripts/seed_cms_admin.py --email admin@stratum.ai --password YourSecurePassword123!

Default Credentials (CHANGE AFTER FIRST LOGIN):
    Email:    cms-admin@stratum.ai
    Password: StratumCMS2024!
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import encrypt_pii, get_password_hash, hash_pii_for_lookup
from app.models import Tenant, User, UserRole

# Default CMS admin credentials (should be changed after first login)
DEFAULT_EMAIL = "cms-admin@stratum.ai"
DEFAULT_PASSWORD = "StratumCMS2024!"
DEFAULT_NAME = "CMS Root Admin"
DEFAULT_TENANT_NAME = "Stratum Platform"
DEFAULT_TENANT_SLUG = "stratum-platform"


async def seed_cms_admin(email: str, password: str, name: str):
    """Create protected CMS root admin."""

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("  Stratum AI - CMS Root Admin Setup")
    print("=" * 60)

    async with async_session() as db:
        try:
            # Check if protected admin already exists
            result = await db.execute(select(User).where(User.is_protected == True))
            existing_protected = result.scalar_one_or_none()

            if existing_protected:
                print(f"\n[!] Protected admin already exists (ID: {existing_protected.id})")
                print("    This account cannot be recreated.")
                print("\n    To reset, you must manually update the database.")
                return

            # Check if user with this email already exists
            email_hash = hash_pii_for_lookup(email.lower())
            result = await db.execute(select(User).where(User.email_hash == email_hash))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"\n[!] User with email {email} already exists (ID: {existing_user.id})")
                print("    Making this user the protected root admin...")
                existing_user.role = UserRole.SUPERADMIN
                existing_user.is_protected = True
                existing_user.is_active = True
                existing_user.is_verified = True
                await db.commit()
                print(f"    User {existing_user.id} is now the protected root admin.")
                return

            # Check for existing platform tenant or create one
            result = await db.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG))
            tenant = result.scalar_one_or_none()

            if not tenant:
                # Try to get first tenant
                result = await db.execute(select(Tenant).limit(1))
                tenant = result.scalar_one_or_none()

            if not tenant:
                print("\n[1/2] Creating platform tenant...")
                tenant = Tenant(
                    name=DEFAULT_TENANT_NAME,
                    slug=DEFAULT_TENANT_SLUG,
                    plan="enterprise",
                    settings={"timezone": "UTC", "currency": "USD"},
                    feature_flags={"cms_access": True, "superadmin": True},
                    max_users=999,
                    max_campaigns=9999,
                )
                db.add(tenant)
                await db.flush()
                print(f"      Created tenant: {tenant.name} (ID: {tenant.id})")
            else:
                print(f"\n[1/2] Using existing tenant: {tenant.name} (ID: {tenant.id})")

            print("\n[2/2] Creating protected CMS root admin...")
            user = User(
                email=encrypt_pii(email.lower()),
                email_hash=email_hash,
                password_hash=get_password_hash(password),
                full_name=encrypt_pii(name),
                role=UserRole.SUPERADMIN,
                tenant_id=tenant.id,
                is_verified=True,
                is_active=True,
                is_protected=True,  # This account cannot be deleted or demoted
                permissions={"all": True},
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            print(f"      Created user: {email}")
            print(f"      User ID: {user.id}")
            print(f"      Role: {user.role.value}")
            print("      Protected: Yes (cannot be deleted or demoted)")

            print("\n" + "=" * 60)
            print("  CMS Root Admin created successfully!")
            print("=" * 60)
            print("\n  Login at: /cms-login")
            print("\n  Credentials:")
            print(f"    Email:     {email}")
            print(f"    Password:  {password}")
            print("\n  IMPORTANT: Change the password after first login!")
            print("\n  This account can:")
            print("    - Access CMS at /cms")
            print("    - Add other admin users")
            print("    - Manage all content")
            print("\n  This account CANNOT be:")
            print("    - Deleted by other admins")
            print("    - Demoted to a lower role")
            print("    - Deactivated by other admins")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[ERROR] Failed to create CMS admin: {e}")
            await db.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description="Create protected CMS root admin account")
    parser.add_argument(
        "--email", default=DEFAULT_EMAIL, help=f"Admin email (default: {DEFAULT_EMAIL})"
    )
    parser.add_argument(
        "--password", default=DEFAULT_PASSWORD, help="Admin password (default: hidden)"
    )
    parser.add_argument(
        "--name", default=DEFAULT_NAME, help=f"Admin display name (default: {DEFAULT_NAME})"
    )

    args = parser.parse_args()

    # Validate password strength
    if len(args.password) < 8:
        print("[ERROR] Password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(seed_cms_admin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
