# =============================================================================
# Stratum AI - Application Configuration
# =============================================================================
"""
Centralized configuration management using Pydantic Settings.
All environment variables are validated and typed.
"""

import re
import warnings
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and type hints."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(default="Stratum AI", description="Application name")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for signing",
    )
    api_v1_prefix: str = Field(default="/api/v1")

    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://stratum:stratum_secure_password_2024@localhost:5432/stratum_ai"
    )
    database_url_sync: str = Field(
        default="postgresql://stratum:stratum_secure_password_2024@localhost:5432/stratum_ai"
    )
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_recycle: int = Field(default=3600)

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_async_driver(cls, v: str) -> str:
        """Convert Railway/Heroku postgresql:// to postgresql+asyncpg:// for async engine."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("database_url_sync", mode="before")
    @classmethod
    def ensure_sync_driver(cls, v: str) -> str:
        """Ensure sync URL uses standard postgresql:// driver."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql://", 1)
            if v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql+asyncpg://", "postgresql://", 1)
        return v

    # -------------------------------------------------------------------------
    # Redis Configuration
    # -------------------------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # -------------------------------------------------------------------------
    # ML Provider Configuration
    # -------------------------------------------------------------------------
    ml_provider: Literal["local", "vertex"] = Field(
        default="local",
        description="ML inference provider: 'local' for scikit-learn or 'vertex' for Google Vertex AI",
    )
    ml_models_path: str = Field(default="./ml_models")
    google_cloud_project: Optional[str] = Field(default=None)
    vertex_ai_endpoint: Optional[str] = Field(default=None)
    google_application_credentials: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # Ad Platform Configuration
    # -------------------------------------------------------------------------
    use_mock_ad_data: bool = Field(
        default=False, description="Use mock data instead of real ad platform APIs (dev only)"
    )

    # Meta/Facebook
    meta_app_id: Optional[str] = Field(default=None)
    meta_app_secret: Optional[str] = Field(default=None)
    meta_access_token: Optional[str] = Field(default=None)
    meta_api_version: str = Field(default="v21.0")
    meta_ad_account_ids: Optional[str] = Field(default=None)

    # Google Ads
    google_ads_developer_token: Optional[str] = Field(default=None)
    google_ads_client_id: Optional[str] = Field(default=None)
    google_ads_client_secret: Optional[str] = Field(default=None)
    google_ads_refresh_token: Optional[str] = Field(default=None)
    google_ads_customer_id: Optional[str] = Field(default=None)

    # TikTok
    tiktok_app_id: Optional[str] = Field(default=None)
    tiktok_secret: Optional[str] = Field(default=None)
    tiktok_access_token: Optional[str] = Field(default=None)
    tiktok_advertiser_id: Optional[str] = Field(default=None)

    # Snapchat
    snapchat_client_id: Optional[str] = Field(default=None)
    snapchat_client_secret: Optional[str] = Field(default=None)
    snapchat_access_token: Optional[str] = Field(default=None)
    snapchat_ad_account_id: Optional[str] = Field(default=None)

    # LinkedIn
    linkedin_client_id: Optional[str] = Field(
        default=None, description="LinkedIn App Client ID"
    )
    linkedin_client_secret: Optional[str] = Field(
        default=None, description="LinkedIn App Client Secret"
    )
    linkedin_access_token: Optional[str] = Field(
        default=None, description="LinkedIn Marketing API access token"
    )

    # -------------------------------------------------------------------------
    # WhatsApp Business API Configuration
    # -------------------------------------------------------------------------
    whatsapp_phone_number_id: Optional[str] = Field(
        default=None, description="WhatsApp Business Phone Number ID"
    )
    whatsapp_access_token: Optional[str] = Field(
        default=None, description="WhatsApp Business API access token"
    )
    whatsapp_business_account_id: Optional[str] = Field(
        default=None, description="WhatsApp Business Account ID"
    )
    whatsapp_verify_token: str = Field(
        default="stratum-whatsapp-verify-token",
        description="Token for webhook verification"
    )
    whatsapp_app_secret: Optional[str] = Field(
        default=None, description="WhatsApp/Meta App Secret for webhook signature verification"
    )
    whatsapp_api_version: str = Field(
        default="v18.0", description="WhatsApp/Meta Graph API version"
    )

    # -------------------------------------------------------------------------
    # HubSpot CRM Configuration
    # -------------------------------------------------------------------------
    hubspot_client_id: Optional[str] = Field(
        default=None, description="HubSpot OAuth App Client ID"
    )
    hubspot_client_secret: Optional[str] = Field(
        default=None, description="HubSpot OAuth App Client Secret"
    )
    hubspot_api_key: Optional[str] = Field(
        default=None, description="HubSpot API Key (legacy, prefer OAuth)"
    )

    # -------------------------------------------------------------------------
    # Market Intelligence Configuration
    # -------------------------------------------------------------------------
    market_intel_provider: Literal["mock", "serpapi", "dataforseo"] = Field(
        default="mock"
    )
    serpapi_key: Optional[str] = Field(default=None)
    dataforseo_login: Optional[str] = Field(default=None)
    dataforseo_password: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # Security Configuration
    # -------------------------------------------------------------------------
    jwt_secret_key: str = Field(
        default="jwt-secret-dev", description="JWT signing key"
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    pii_encryption_key: str = Field(
        default="dev-encryption-key-32bytes", description="AES encryption key for PII"
    )

    # -------------------------------------------------------------------------
    # CORS Configuration
    # -------------------------------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173"
    )
    cors_allow_credentials: bool = Field(default=True)

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_format: Literal["json", "console"] = Field(default="json")
    sentry_dsn: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # SMTP / Email Configuration
    # -------------------------------------------------------------------------
    smtp_host: Optional[str] = Field(default=None, description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_tls: bool = Field(default=True, description="Use STARTTLS")
    smtp_ssl: bool = Field(default=False, description="Use SSL")
    email_from_name: str = Field(default="Stratum AI", description="Sender display name")
    email_from_address: str = Field(
        default="noreply@stratumhq.com", description="Sender email address"
    )
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend base URL for email links"
    )
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8000", description="Base URL for OAuth redirect callbacks"
    )
    email_verification_expire_hours: int = Field(
        default=24, description="Email verification token TTL in hours"
    )
    password_reset_expire_hours: int = Field(
        default=1, description="Password reset token TTL in hours"
    )

    # -------------------------------------------------------------------------
    # Stripe Payments Configuration
    # -------------------------------------------------------------------------
    stripe_secret_key: Optional[str] = Field(default=None, description="Stripe secret API key")
    stripe_publishable_key: Optional[str] = Field(default=None, description="Stripe publishable key")
    stripe_webhook_secret: Optional[str] = Field(default=None, description="Stripe webhook signing secret")

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_burst: int = Field(default=20)

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    feature_competitor_intel: bool = Field(default=True)
    feature_what_if_simulator: bool = Field(default=True)
    feature_automation_rules: bool = Field(default=True)
    feature_gdpr_compliance: bool = Field(default=True)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @model_validator(mode="after")
    def derive_sync_url_from_async(self) -> "Settings":
        """If DATABASE_URL_SYNC was not explicitly set, derive it from DATABASE_URL."""
        default_sync = "postgresql://stratum:stratum_secure_password_2024@localhost:5432/stratum_ai"
        if self.database_url_sync == default_sync and self.database_url != (
            "postgresql+asyncpg://stratum:stratum_secure_password_2024@localhost:5432/stratum_ai"
        ):
            # DATABASE_URL was overridden (e.g. by Railway) but DATABASE_URL_SYNC was not
            sync_url = self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
            object.__setattr__(self, "database_url_sync", sync_url)
        return self

    @model_validator(mode="after")
    def validate_security_keys(self) -> "Settings":
        """Emit warnings for short keys, weak patterns, and insecure DB passwords."""
        # --- Short key warnings (< 32 chars) ---
        key_checks = {
            "SECRET_KEY": self.secret_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "PII_ENCRYPTION_KEY": self.pii_encryption_key,
        }
        for label, value in key_checks.items():
            if len(value) < 32:
                warnings.warn(
                    f"SECURITY WARNING: {label} must be set and be at least 32 "
                    f"characters long (current length: {len(value)})"
                )

        # --- Weak pattern detection in secret_key ---
        weak_patterns = ["dev", "changeme", "test", "placeholder", "insecure"]
        for pattern in weak_patterns:
            if pattern in self.secret_key.lower():
                warnings.warn(
                    f"SECURITY WARNING: SECRET_KEY contains weak pattern '{pattern}'. "
                    "Use a strong random key in production."
                )
                break  # one warning is enough

        # --- Insecure database password detection ---
        insecure_passwords = ["changeme", "password", "123456", "admin", "root"]
        db_url = self.database_url or ""
        match = re.search(r"://[^:]+:([^@]+)@", db_url)
        if match:
            db_password = match.group(1)
            if db_password in insecure_passwords:
                warnings.warn(
                    f"SECURITY WARNING: database URL contains insecure password '{db_password}'. "
                    "Use a strong password in production."
                )

        return self

    @model_validator(mode="after")
    def enforce_production_safety(self) -> "Settings":
        """Reject insecure default values in production and staging environments."""
        if self.app_env in ("production", "staging"):
            if self.secret_key == "dev-secret-key-change-in-production":
                raise ValueError(
                    f"secret_key must be changed from its default value in {self.app_env}"
                )
            if self.jwt_secret_key == "jwt-secret-dev":
                raise ValueError(
                    f"jwt_secret_key must be changed from its default value in {self.app_env}"
                )
            if self.pii_encryption_key == "dev-encryption-key-32bytes":
                raise ValueError(
                    f"pii_encryption_key must be changed from its default value in {self.app_env}"
                )
            if (
                self.whatsapp_verify_token == "stratum-whatsapp-verify-token"
                and self.whatsapp_phone_number_id  # truthy check: None and "" both skip
            ):
                raise ValueError(
                    f"whatsapp_verify_token must be changed from its default value in {self.app_env} "
                    "when WhatsApp is configured"
                )
            if self.use_mock_ad_data is True:
                raise ValueError(
                    f"use_mock_ad_data must be False in {self.app_env} — production must use real API data"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
