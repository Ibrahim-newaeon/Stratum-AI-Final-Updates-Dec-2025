# =============================================================================
# Stratum AI - Application Configuration
# =============================================================================
"""
Centralized configuration management using Pydantic Settings.
All environment variables are validated and typed.
"""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, field_validator
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
    debug: bool = Field(default=True)
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=32,
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
        default="http://localhost:8000",
        description="Base URL for OAuth callbacks"
    )

    # Meta/Facebook OAuth
    meta_app_id: Optional[str] = Field(default=None, description="Meta/Facebook App ID")
    meta_app_secret: Optional[str] = Field(default=None, description="Meta/Facebook App Secret")
    meta_access_token: Optional[str] = Field(default=None)
    meta_api_version: str = Field(default="v19.0", description="Meta Graph API version")

    # Google Ads OAuth
    google_ads_developer_token: Optional[str] = Field(default=None)
    google_ads_client_id: Optional[str] = Field(default=None, description="Google OAuth Client ID")
    google_ads_client_secret: Optional[str] = Field(default=None, description="Google OAuth Client Secret")
    google_ads_refresh_token: Optional[str] = Field(default=None)
    google_ads_customer_id: Optional[str] = Field(default=None)

    # TikTok OAuth
    tiktok_app_id: Optional[str] = Field(default=None, description="TikTok App ID")
    tiktok_app_secret: Optional[str] = Field(default=None, description="TikTok App Secret")
    tiktok_secret: Optional[str] = Field(default=None)  # Legacy, use tiktok_app_secret
    tiktok_access_token: Optional[str] = Field(default=None)

    # Snapchat OAuth
    snapchat_client_id: Optional[str] = Field(default=None, description="Snapchat Client ID")
    snapchat_client_secret: Optional[str] = Field(default=None, description="Snapchat Client Secret")
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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
