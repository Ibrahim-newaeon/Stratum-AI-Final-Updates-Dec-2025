# =============================================================================
# Stratum AI - Configuration Validation Test Suite
# =============================================================================
"""
Tests verifying that the Settings class correctly validates configuration:
- Weak/default keys are detected
- Database URL normalization works
- Required security fields are enforced
- Environment-specific behavior (dev vs production)
- Stripe configuration validation
"""

import os
import warnings

import pytest

# ---------------------------------------------------------------------------
# Helper: create a Settings instance with specific env vars
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    """Create a fresh Settings instance with specific overrides.

    We import Settings inside the function to avoid module-level side effects
    from the global settings singleton, and we pass overrides as environment
    variables.
    """
    # Save and set env vars
    saved = {}
    for key, val in overrides.items():
        env_key = key.upper()
        saved[env_key] = os.environ.get(env_key)
        os.environ[env_key] = str(val)

    try:
        # Import fresh to avoid cached settings
        from app.core.config import Settings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            s = Settings()
        return s, w
    finally:
        # Restore env vars
        for env_key, old_val in saved.items():
            if old_val is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = old_val


# ---------------------------------------------------------------------------
# 1. Security Key Validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityKeyValidation:
    """Tests that weak or missing security keys produce warnings."""

    def test_short_secret_key_warns(self) -> None:
        """A SECRET_KEY shorter than 32 chars triggers a warning."""
        _, w = _make_settings(
            secret_key="tooshort",
            jwt_secret_key="a" * 32,
            pii_encryption_key="b" * 32,
        )
        warning_messages = [str(warning.message) for warning in w]
        assert any("SECRET_KEY" in msg for msg in warning_messages)

    def test_short_jwt_key_warns(self) -> None:
        """A JWT_SECRET_KEY shorter than 32 chars triggers a warning."""
        _, w = _make_settings(
            secret_key="a" * 32,
            jwt_secret_key="short",
            pii_encryption_key="b" * 32,
        )
        warning_messages = [str(warning.message) for warning in w]
        assert any("JWT_SECRET_KEY" in msg for msg in warning_messages)

    def test_short_pii_key_warns(self) -> None:
        """A PII_ENCRYPTION_KEY shorter than 32 chars triggers a warning."""
        _, w = _make_settings(
            secret_key="a" * 32,
            jwt_secret_key="b" * 32,
            pii_encryption_key="short",
        )
        warning_messages = [str(warning.message) for warning in w]
        assert any("PII_ENCRYPTION_KEY" in msg for msg in warning_messages)

    def test_strong_keys_no_key_length_warning(self) -> None:
        """Strong 32+ char random keys should not trigger length warnings."""
        import secrets

        _, w = _make_settings(
            secret_key=secrets.token_urlsafe(32),
            jwt_secret_key=secrets.token_urlsafe(32),
            pii_encryption_key=secrets.token_urlsafe(32),
        )
        # Filter for length-related warnings only
        length_warnings = [
            str(warning.message)
            for warning in w
            if "must be set and be at least 32" in str(warning.message)
        ]
        assert len(length_warnings) == 0


# ---------------------------------------------------------------------------
# 2. Weak Key Pattern Detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWeakKeyPatterns:
    """Tests that common weak key patterns are detected."""

    @pytest.mark.parametrize(
        "weak_value",
        [
            "dev-secret-key-that-is-long-enough-32chars",
            "changeme-this-is-my-super-long-secret-key",
            "test-key-long-enough-for-thirty-two-chars",
            "placeholder-value-that-is-really-long-xxx",
            "insecure-key-aaaaaaaaaaaaaaaaaaaaaaaaa",
        ],
    )
    def test_weak_patterns_detected(self, weak_value: str) -> None:
        """Keys containing common weak patterns produce warnings."""
        _, w = _make_settings(
            secret_key=weak_value,
            jwt_secret_key="x" * 32,
            pii_encryption_key="y" * 32,
        )
        warning_messages = " ".join(str(warning.message) for warning in w)
        assert "weak" in warning_messages.lower() or "SECURITY WARNING" in warning_messages


# ---------------------------------------------------------------------------
# 3. Database URL Normalization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDatabaseURLNormalization:
    """Tests for automatic database URL driver normalization."""

    def test_async_url_gets_asyncpg_driver(self) -> None:
        """DATABASE_URL starting with postgresql:// gets asyncpg driver added."""
        s, _ = _make_settings(
            database_url="postgresql://user:pass@localhost:5432/db",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        assert s.database_url.startswith("postgresql+asyncpg://")

    def test_postgres_shorthand_normalized(self) -> None:
        """DATABASE_URL starting with postgres:// (Heroku/Railway style) is normalized."""
        s, _ = _make_settings(
            database_url="postgres://user:pass@host:5432/db",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        assert s.database_url.startswith("postgresql+asyncpg://")

    def test_sync_url_strips_asyncpg(self) -> None:
        """DATABASE_URL_SYNC should NOT have asyncpg driver."""
        s, _ = _make_settings(
            database_url_sync="postgresql+asyncpg://user:pass@localhost:5432/db",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        assert not s.database_url_sync.startswith("postgresql+asyncpg://")
        assert s.database_url_sync.startswith("postgresql://")


# ---------------------------------------------------------------------------
# 4. Environment Properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnvironmentProperties:
    """Tests for environment detection properties."""

    def test_is_development_true_by_default(self) -> None:
        """Default APP_ENV is 'development'."""
        s, _ = _make_settings(
            app_env="development",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        assert s.is_development is True
        assert s.is_production is False

    def test_is_production_when_set(self) -> None:
        """APP_ENV=production sets is_production to True."""
        s, _ = _make_settings(
            app_env="production",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
            use_mock_ad_data="false",
        )
        assert s.is_production is True
        assert s.is_development is False


# ---------------------------------------------------------------------------
# 5. Insecure Database Password Detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInsecureDatabasePasswords:
    """Tests that default/weak database passwords produce warnings."""

    @pytest.mark.parametrize(
        "weak_password",
        ["changeme", "password", "123456", "admin", "root"],
    )
    def test_weak_db_password_warns(self, weak_password: str) -> None:
        """Database URLs containing weak passwords produce warnings."""
        _, w = _make_settings(
            database_url=f"postgresql+asyncpg://user:{weak_password}@localhost:5432/db",
            database_url_sync=f"postgresql://user:{weak_password}@localhost:5432/db",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        warning_messages = " ".join(str(warning.message) for warning in w)
        assert "insecure password" in warning_messages.lower() or "SECURITY WARNING" in warning_messages


# ---------------------------------------------------------------------------
# 6. CORS Configuration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCORSConfiguration:
    """Tests for CORS origins parsing."""

    def test_cors_origins_list_splits_correctly(self) -> None:
        """Comma-separated CORS origins are split into a list."""
        s, _ = _make_settings(
            cors_origins="https://app.stratum.ai,https://staging.stratum.ai",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        assert s.cors_origins_list == [
            "https://app.stratum.ai",
            "https://staging.stratum.ai",
        ]

    def test_cors_origins_handles_spaces(self) -> None:
        """CORS origins with spaces around commas are trimmed."""
        s, _ = _make_settings(
            cors_origins="https://a.com , https://b.com",
            secret_key="x" * 32,
            jwt_secret_key="y" * 32,
            pii_encryption_key="z" * 32,
        )
        assert s.cors_origins_list == ["https://a.com", "https://b.com"]
