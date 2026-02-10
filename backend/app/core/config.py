# =============================================================================
# Stratum AI - Application Configuration
# =============================================================================
"""
Centralized configuration management using Pydantic Settings.
All environment variables are validated and typed.

SECURITY NOTE:
- In production, all sensitive values MUST be set via environment variables
- Never commit real credentials to the repository
- Use strong, randomly generated keys (32+ bytes) for encryption/signing
"""

import warnings
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, model_validator
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
    app_env: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=True)
    secret_key: str = Field(
        default="",
        min_length=32,
        description="Secret key for signing (REQUIRED: set via SECRET_KEY env var)",
    )
    api_v1_prefix: str = Field(default="/api/v1")

    # -------------------------------------------------------------------------
    # Subscription Tier
    # -------------------------------------------------------------------------
    subscription_tier: Literal["starter", "professional", "enterprise"] = Field(
        default="enterprise", description="Subscription tier (starter, professional, enterprise)"
    )

    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    # NOTE: No default passwords - must be set via environment variables
    database_url: str = Field(
        default="postgresql+asyncpg://stratum:changeme@localhost:5432/stratum_ai",
        description="Database URL (set DATABASE_URL env var with real credentials)",
    )
    database_url_sync: str = Field(
        default="postgresql://stratum:changeme@localhost:5432/stratum_ai",
        description="Sync database URL (set DATABASE_URL_SYNC env var with real credentials)",
    )
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_recycle: int = Field(default=3600)

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
        default=True, description="Use mock data instead of real ad platform APIs"
    )

    # OAuth callback base URL (for constructing redirect URIs)
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8000", description="Base URL for OAuth callbacks"
    )

    # Meta/Facebook OAuth
    meta_app_id: Optional[str] = Field(default=None, description="Meta/Facebook App ID")
    meta_app_secret: Optional[str] = Field(default=None, description="Meta/Facebook App Secret")
    meta_access_token: Optional[str] = Field(default=None)
    meta_api_version: str = Field(default="v19.0", description="Meta Graph API version")

    # Google Ads OAuth
    google_ads_developer_token: Optional[str] = Field(default=None)
    google_ads_client_id: Optional[str] = Field(default=None, description="Google OAuth Client ID")
    google_ads_client_secret: Optional[str] = Field(
        default=None, description="Google OAuth Client Secret"
    )
    google_ads_refresh_token: Optional[str] = Field(default=None)
    google_ads_customer_id: Optional[str] = Field(default=None)

    # TikTok OAuth
    tiktok_app_id: Optional[str] = Field(default=None, description="TikTok App ID")
    tiktok_app_secret: Optional[str] = Field(default=None, description="TikTok App Secret")
    tiktok_secret: Optional[str] = Field(default=None)  # Legacy, use tiktok_app_secret
    tiktok_access_token: Optional[str] = Field(default=None)

    # Snapchat OAuth
    snapchat_client_id: Optional[str] = Field(default=None, description="Snapchat Client ID")
    snapchat_client_secret: Optional[str] = Field(
        default=None, description="Snapchat Client Secret"
    )
    snapchat_access_token: Optional[str] = Field(default=None)

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
        default="stratum-whatsapp-verify-token", description="Token for webhook verification"
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
    # Zoho CRM Configuration
    # -------------------------------------------------------------------------
    zoho_client_id: Optional[str] = Field(default=None, description="Zoho OAuth App Client ID")
    zoho_client_secret: Optional[str] = Field(
        default=None, description="Zoho OAuth App Client Secret"
    )
    zoho_region: str = Field(
        default="com", description="Zoho data center region (com, eu, in, com.au, jp, com.cn)"
    )

    # -------------------------------------------------------------------------
    # Market Intelligence Configuration
    # -------------------------------------------------------------------------
    market_intel_provider: Literal["mock", "serpapi", "dataforseo"] = Field(default="mock")
    serpapi_key: Optional[str] = Field(default=None)
    dataforseo_login: Optional[str] = Field(default=None)
    dataforseo_password: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # Security Configuration
    # -------------------------------------------------------------------------
    # NOTE: All security keys MUST be set via environment variables in production
    jwt_secret_key: str = Field(
        default="",
        description="JWT signing key (REQUIRED: set via JWT_SECRET_KEY env var, min 32 chars)",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    pii_encryption_key: str = Field(
        default="",
        description="AES encryption key for PII (REQUIRED: set via PII_ENCRYPTION_KEY env var, min 32 chars)",
    )

    # Email verification and password reset token expiry
    email_verification_expire_hours: int = Field(
        default=24, description="Hours until email verification token expires"
    )
    password_reset_expire_hours: int = Field(
        default=1, description="Hours until password reset token expires"
    )

    # -------------------------------------------------------------------------
    # Email Configuration
    # -------------------------------------------------------------------------
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_tls: bool = Field(default=True, description="Use TLS for SMTP")
    smtp_ssl: bool = Field(default=False, description="Use SSL for SMTP")
    email_from_name: str = Field(default="Stratum AI", description="Email sender name")
    email_from_address: str = Field(
        default="noreply@stratum.ai", description="Email sender address"
    )

    # Frontend URL for email links
    frontend_url: str = Field(
        default="http://localhost:3000", description="Frontend URL for email links"
    )

    # -------------------------------------------------------------------------
    # CORS Configuration
    # -------------------------------------------------------------------------
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")
    cors_allow_credentials: bool = Field(default=True)

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")
    sentry_dsn: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_burst: int = Field(default=20)

    # -------------------------------------------------------------------------
    # Stripe Payment Configuration
    # -------------------------------------------------------------------------
    stripe_secret_key: Optional[str] = Field(
        default=None, description="Stripe Secret Key (sk_live_... or sk_test_...)"
    )
    stripe_publishable_key: Optional[str] = Field(
        default=None, description="Stripe Publishable Key (pk_live_... or pk_test_...)"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default=None, description="Stripe Webhook Signing Secret (whsec_...)"
    )
    stripe_starter_price_id: Optional[str] = Field(
        default=None, description="Stripe Price ID for Starter tier (price_...)"
    )
    stripe_professional_price_id: Optional[str] = Field(
        default=None, description="Stripe Price ID for Professional tier (price_...)"
    )
    stripe_enterprise_price_id: Optional[str] = Field(
        default=None, description="Stripe Price ID for Enterprise tier (price_...)"
    )

    # -------------------------------------------------------------------------
    # CDN Cache Invalidation
    # -------------------------------------------------------------------------
    cdn_provider: Optional[Literal["cloudflare", "cloudfront", "fastly"]] = Field(
        default=None, description="CDN provider for cache invalidation (cloudflare, cloudfront, fastly)"
    )
    cdn_api_key: Optional[str] = Field(
        default=None, description="CDN API token (Cloudflare API token or Fastly API token)"
    )
    cdn_zone_id: Optional[str] = Field(
        default=None,
        description="CDN zone/distribution ID (Cloudflare Zone ID or CloudFront Distribution ID)",
    )
    cdn_base_url: Optional[str] = Field(
        default=None, description="Public base URL for full purge URLs (e.g. https://blog.stratum.ai)"
    )

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

    @property
    def stripe_enabled(self) -> bool:
        """Check if Stripe is configured (has secret key)."""
        return bool(self.stripe_secret_key)

    @property
    def stripe_fully_configured(self) -> bool:
        """Check if all Stripe settings are properly configured for payments."""
        return all(
            [
                self.stripe_secret_key,
                self.stripe_publishable_key,
                self.stripe_webhook_secret,
                self.stripe_starter_price_id,
                self.stripe_professional_price_id,
                self.stripe_enterprise_price_id,
            ]
        )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """
        Validate that security-critical settings are properly configured.

        In production:
        - Raises errors for missing/weak security keys
        - Raises errors for default/weak database passwords

        In development:
        - Issues warnings but allows startup with defaults for local testing
        """
        issues = []

        # Check for insecure database passwords
        insecure_passwords = ["changeme", "password", "123456", "admin", "root", ""]
        for url_field in ["database_url", "database_url_sync"]:
            url = getattr(self, url_field, "")
            for weak_pw in insecure_passwords:
                if f":{weak_pw}@" in url:
                    issues.append(f"{url_field} contains insecure password")
                    break

        # Check security keys
        if not self.secret_key or len(self.secret_key) < 32:
            issues.append("SECRET_KEY must be set and be at least 32 characters")

        if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
            issues.append("JWT_SECRET_KEY must be set and be at least 32 characters")

        if not self.pii_encryption_key or len(self.pii_encryption_key) < 32:
            issues.append("PII_ENCRYPTION_KEY must be set and be at least 32 characters")

        # Check for common weak keys and development fallback patterns
        weak_key_patterns = [
            "dev-secret",
            "jwt-secret-dev",
            "dev-encryption",
            "changeme",
            "secret",
            "password",
            "test",
            "demo",
            "dev-only",
            "do-not-use",
            "example",
            "placeholder",
            "your-key",
            "change-me",
            "default",
            "insecure",
        ]
        for key_field in ["secret_key", "jwt_secret_key", "pii_encryption_key"]:
            key_value = getattr(self, key_field, "").lower()
            for weak in weak_key_patterns:
                if weak in key_value:
                    issues.append(
                        f"{key_field.upper()} contains weak/default value (matched: '{weak}')"
                    )
                    break

        # Validate Stripe configuration in production
        # If Stripe secret key is set, all other Stripe settings must also be set
        if self.stripe_secret_key:
            stripe_issues = []
            if not self.stripe_publishable_key:
                stripe_issues.append(
                    "STRIPE_PUBLISHABLE_KEY is required when STRIPE_SECRET_KEY is set"
                )
            if not self.stripe_webhook_secret:
                stripe_issues.append("STRIPE_WEBHOOK_SECRET is required for payment webhooks")
            if not self.stripe_starter_price_id:
                stripe_issues.append(
                    "STRIPE_STARTER_PRICE_ID is required for subscription checkout"
                )
            if not self.stripe_professional_price_id:
                stripe_issues.append(
                    "STRIPE_PROFESSIONAL_PRICE_ID is required for subscription checkout"
                )
            if not self.stripe_enterprise_price_id:
                stripe_issues.append(
                    "STRIPE_ENTERPRISE_PRICE_ID is required for subscription checkout"
                )

            # Check for test keys in production
            if self.is_production:
                if self.stripe_secret_key.startswith("sk_test_"):
                    stripe_issues.append(
                        "STRIPE_SECRET_KEY is using test key in production (should be sk_live_...)"
                    )
                if self.stripe_publishable_key and self.stripe_publishable_key.startswith(
                    "pk_test_"
                ):
                    stripe_issues.append(
                        "STRIPE_PUBLISHABLE_KEY is using test key in production (should be pk_live_...)"
                    )

            if stripe_issues:
                issues.extend(stripe_issues)

        if issues:
            if self.is_production:
                # In production, fail fast with clear error
                raise ValueError(
                    "SECURITY ERROR - Cannot start in production with insecure configuration:\n"
                    "  - " + "\n  - ".join(issues) + "\n\n"
                    "Please set these environment variables with secure values:\n"
                    "  - DATABASE_URL (with strong password)\n"
                    "  - SECRET_KEY (min 32 random characters)\n"
                    "  - JWT_SECRET_KEY (min 32 random characters)\n"
                    "  - PII_ENCRYPTION_KEY (min 32 random characters)\n\n"
                    'Generate secure keys with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            else:
                # In development, warn but allow startup
                warning_msg = (
                    f"\n{'='*60}\n"
                    f"SECURITY WARNING - Development mode with insecure defaults:\n"
                    f"  - " + "\n  - ".join(issues) + "\n"
                    f"{'='*60}\n"
                    f"This is OK for local development but NEVER use in production!\n"
                    f"Set APP_ENV=production to enforce security requirements.\n"
                    f"{'='*60}\n"
                )
                warnings.warn(warning_msg, UserWarning, stacklevel=2)

        return self


# Development-only fallback keys (only used when APP_ENV != production)
_DEV_FALLBACK_KEYS = {
    "secret_key": "dev-only-secret-key-do-not-use-in-production-32chars",
    "jwt_secret_key": "dev-only-jwt-secret-do-not-use-in-production-32",
    "pii_encryption_key": "dev-only-pii-key-do-not-use-in-prod-32ch",
}


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    In development mode, provides fallback values for required keys
    to allow local testing without full configuration.
    """
    import os

    # Check if we're in production before creating settings
    app_env = os.getenv("APP_ENV", "development").lower()

    if app_env != "production":
        # For development, set fallback values if not provided
        for key, fallback in _DEV_FALLBACK_KEYS.items():
            env_key = key.upper()
            if not os.getenv(env_key):
                os.environ[env_key] = fallback

    return Settings()


# Global settings instance
settings = get_settings()
