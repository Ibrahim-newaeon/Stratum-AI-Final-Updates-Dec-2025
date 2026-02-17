# =============================================================================
# Stratum AI - Multi-Factor Authentication Fields Migration
# =============================================================================
"""
Add MFA/2FA fields to the users table for TOTP-based authentication.

Fields added:
- totp_secret: Encrypted TOTP secret key
- totp_enabled: Whether MFA is enabled for the user
- totp_verified_at: When MFA was verified/enabled
- backup_codes: JSON array of hashed backup codes
- failed_totp_attempts: Counter for rate limiting
- totp_lockout_until: Timestamp for account lockout

Revision ID: 033_add_mfa_fields
Revises: 032_add_row_level_security
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# Revision identifiers
revision = "033_add_mfa_fields"
down_revision = "032_add_row_level_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add MFA fields to users table."""

    # Add TOTP secret (encrypted)
    op.add_column(
        "users",
        sa.Column(
            "totp_secret",
            sa.String(255),
            nullable=True,
            comment="Encrypted TOTP secret key for authenticator apps",
        ),
    )

    # Add TOTP enabled flag
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether 2FA/MFA is enabled for this user",
        ),
    )

    # Add TOTP verified timestamp
    op.add_column(
        "users",
        sa.Column(
            "totp_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When MFA was verified and enabled",
        ),
    )

    # Add backup codes (JSONB for storing hashed codes)
    op.add_column(
        "users",
        sa.Column(
            "backup_codes",
            JSONB,
            nullable=True,
            comment="Hashed backup codes for account recovery",
        ),
    )

    # Add failed TOTP attempts counter
    op.add_column(
        "users",
        sa.Column(
            "failed_totp_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of failed MFA attempts (for rate limiting)",
        ),
    )

    # Add lockout timestamp
    op.add_column(
        "users",
        sa.Column(
            "totp_lockout_until",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Account locked until this time due to failed MFA attempts",
        ),
    )

    # Add index for MFA-enabled users (useful for reporting)
    op.create_index(
        "ix_users_totp_enabled",
        "users",
        ["totp_enabled"],
        postgresql_where=sa.text("totp_enabled = true"),
    )

    # Add index for locked accounts (useful for admin monitoring)
    op.create_index(
        "ix_users_totp_lockout",
        "users",
        ["totp_lockout_until"],
        postgresql_where=sa.text("totp_lockout_until IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove MFA fields from users table."""

    # Drop indexes
    op.drop_index("ix_users_totp_lockout", table_name="users")
    op.drop_index("ix_users_totp_enabled", table_name="users")

    # Drop columns
    op.drop_column("users", "totp_lockout_until")
    op.drop_column("users", "failed_totp_attempts")
    op.drop_column("users", "backup_codes")
    op.drop_column("users", "totp_verified_at")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
