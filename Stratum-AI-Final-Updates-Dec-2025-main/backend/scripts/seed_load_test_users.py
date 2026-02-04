#!/usr/bin/env python3
"""
Stratum AI - Multiple Load Test Users Seed Script

Creates multiple test users for k6 load testing to avoid rate limiting.
Each user has their own rate limit bucket (100 req/min).

Usage:
    docker compose exec api python scripts/seed_load_test_users.py
    docker compose exec api python scripts/seed_load_test_users.py --count 50

Default creates 25 users (matching default VU count for load tests).
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

# Load test user credentials template
TEST_PASSWORD = "TestPassword123!"
TEST_TENANT_NAME = "Load Test Tenant"
TEST_TENANT_SLUG = "load-test-tenant"


def get_test_email(index: int) -> str:
    """Generate test email for given index."""
    if index == 0:
        return "admin@test-tenant.com"
    return f"loadtest{index}@test-tenant.com"


async def seed_load_test_users(count: int = 25):
    """Create multiple load test users."""

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("  Stratum AI - Multiple Load Test Users Setup")
    print("=" * 60)
    print(f"\n  Creating {count} load test users...")

    async with async_session() as db:
        try:
            # Get or create tenant
            result = await db.execute(select(Tenant).where(Tenant.id == 1))
            tenant = result.scalar_one_or_none()

            if not tenant:
                result = await db.execute(select(Tenant).where(Tenant.slug == TEST_TENANT_SLUG))
                tenant = result.scalar_one_or_none()

            if not tenant:
                print("\n[!] Creating load test tenant...")
                tenant = Tenant(
                    name=TEST_TENANT_NAME,
                    slug=TEST_TENANT_SLUG,
                    settings={"timezone": "UTC", "currency": "USD"},
                )
                db.add(tenant)
                await db.flush()
                print(f"    Created tenant: {tenant.name} (ID: {tenant.id})")
            else:
                print(f"\n[*] Using existing tenant: {tenant.name} (ID: {tenant.id})")

            created_users = []
            skipped_users = []

            print(f"\n[*] Processing {count} users...\n")

            for i in range(count):
                email = get_test_email(i)
                email_hash = hash_pii_for_lookup(email.lower())

                # Check if user already exists
                result = await db.execute(select(User).where(User.email_hash == email_hash))
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    skipped_users.append(email)
                    continue

                # Create user
                user = User(
                    email=encrypt_pii(email.lower()),
                    email_hash=email_hash,
                    password_hash=get_password_hash(TEST_PASSWORD),
                    full_name=encrypt_pii(f"Load Test User {i}"),
                    role=UserRole.ADMIN,
                    tenant_id=tenant.id,
                    is_verified=True,
                    is_active=True,
                )
                db.add(user)
                created_users.append(email)

                # Flush every 10 users to avoid memory issues
                if len(created_users) % 10 == 0:
                    await db.flush()
                    print(f"    Created {len(created_users)} users...")

            await db.commit()

            print("\n" + "=" * 60)
            print("  Load Test Users Summary")
            print("=" * 60)
            print(f"\n  Created: {len(created_users)} new users")
            print(f"  Skipped: {len(skipped_users)} existing users")
            print(f"  Tenant ID: {tenant.id}")
            print(f"\n  All users use password: {TEST_PASSWORD}")

            if created_users:
                print("\n  New users created:")
                for email in created_users[:5]:
                    print(f"    - {email}")
                if len(created_users) > 5:
                    print(f"    ... and {len(created_users) - 5} more")

            print("\n" + "=" * 60)
            print("  Update your k6 test to use multiple users:")
            print("=" * 60)
            print("""
  // In your k6 test, add user rotation:
  const USERS = [];
  for (let i = 0; i < 25; i++) {
      USERS.push({
          email: i === 0 ? 'admin@test-tenant.com' : `loadtest${i}@test-tenant.com`,
          password: 'TestPassword123!'
      });
  }

  // In setup() or default():
  const userIndex = __VU % USERS.length;
  const user = USERS[userIndex];
""")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[ERROR] Failed to create load test users: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create multiple load test users")
    parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of users to create (default: 25)",
    )
    args = parser.parse_args()

    asyncio.run(seed_load_test_users(args.count))
