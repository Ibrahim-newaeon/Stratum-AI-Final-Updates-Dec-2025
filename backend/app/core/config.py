# =============================================================================
# Stratum AI - Application Configuration
# =============================================================================
"""
Centralized configuration management using Pydantic Settings.
All environment variables are validated and typed.
"""

import re
import secrets
import warnings
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Generate cryptographically secure defaults so the application never
# silently runs with a well-known, guessable key.  These are regenerated
# every process start, which forces operators to set stable values via
# environment variables for any non-ephemeral deployment.
_DEV_SECRET_KEY = f"dev-autogen-{secrets.token_urlsafe(32)}"
_DEV_JWT_SECRET = f"jwt-autogen-{secrets.token_urlsafe(32)}"
_DEV_PII_KEY = secrets.token_urlsafe(32)  # 43-char URL-safe string


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
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    secret_key: str = Field(
        default_factory=lambda: _DEV_SECRET_KEY,
        description="Secret key for signing",
    )
    api_v1_prefix: str = Field(default="/api/v1")

    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai"
    )
    database_url_sync: str = Field(
        default="postgresql://stratum:password@localhost:5432/stratum_ai"
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
    ml_auto_train: bool = Field(
        default=True,
        description="Train ML models from sample data at startup when none are "
        "found. Defaults on (a fresh Railway deploy self-heals). Set false in "
        "CI/health-check environments where blocking startup on training would "
        "exhaust memory and fail the health probe.",
    )
    google_cloud_project: Optional[str] = Field(default=None)
    vertex_ai_endpoint: Optional[str] = Field(default=None)
    google_application_credentials: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # Ad Platform Configuration
    # -------------------------------------------------------------------------
    use_mock_ad_data: bool = Field(
        default=False,
        description="Use mock data instead of real ad platform APIs (dev only)",
    )

    # Meta/Facebook
    meta_app_id: Optional[str] = Field(default=None)
    meta_app_secret: Optional[str] = Field(default=None)
    meta_access_token: Optional[str] = Field(default=None)
    meta_api_version: str = Field(default="v25.0")
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
        default="",
        description="Token for webhook verification — must be set via WHATSAPP_VERIFY_TOKEN env var",
    )
    whatsapp_app_secret: Optional[str] = Field(
        default=None,
        description="WhatsApp/Meta App Secret for webhook signature verification",
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
    # Pipedrive CRM Configuration
    # -------------------------------------------------------------------------
    pipedrive_client_id: Optional[str] = Field(
        default=None, description="Pipedrive OAuth App Client ID"
    )
    pipedrive_client_secret: Optional[str] = Field(
        default=None, description="Pipedrive OAuth App Client Secret"
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
        default_factory=lambda: _DEV_JWT_SECRET, description="JWT signing key"
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    pii_encryption_key: str = Field(
        default_factory=lambda: _DEV_PII_KEY, description="AES encryption key for PII"
    )

    # -------------------------------------------------------------------------
    # CORS Configuration
    # -------------------------------------------------------------------------
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")
    cors_allow_credentials: bool = Field(default=True)

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list, always including frontend_url."""
        origins = [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]
        # Always include frontend_url so cross-origin requests from the
        # frontend are never blocked due to a missing CORS_ORIGINS entry.
        frontend = self.frontend_url.strip().rstrip("/")
        if frontend and frontend not in origins:
            origins.append(frontend)
        return origins

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_format: Literal["json", "console"] = Field(default="json")
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_traces_sample_rate: float = Field(
        default=0.1, description="Sentry performance traces sample rate (0.0-1.0)"
    )
    sentry_profiles_sample_rate: float = Field(
        default=0.1, description="Sentry profiling sample rate (0.0-1.0)"
    )
    sentry_release: Optional[str] = Field(
        default=None, description="Sentry release tag (e.g. git SHA or version)"
    )
    # P0 on-call alerting (MON-002). An incoming-webhook URL (Slack / PagerDuty
    # Events v2 / Opsgenie / generic) that the monitoring task POSTs critical
    # pipeline-health failures to. The escalation code already exists; this
    # declares the setting so it is actually wired (was read via getattr and
    # therefore always None/off).
    alert_webhook_url: Optional[str] = Field(
        default=None,
        description="Incoming webhook for critical (P0) operational alerts",
    )

    # -------------------------------------------------------------------------
    # SMTP / Email Configuration
    # -------------------------------------------------------------------------
    smtp_host: Optional[str] = Field(default=None, description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_tls: bool = Field(default=True, description="Use STARTTLS")
    smtp_ssl: bool = Field(default=False, description="Use SSL")
    sendgrid_api_key: Optional[str] = Field(
        default=None, description="SendGrid API key (preferred over SMTP)"
    )
    sendgrid_webhook_token: Optional[str] = Field(
        default=None,
        description="Secret token for verifying SendGrid inbound webhooks",
    )
    email_from_name: str = Field(
        default="Stratum AI", description="Sender display name"
    )
    email_from_address: str = Field(
        default="noreply@stratumai.app", description="Sender email address"
    )
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend base URL for email links"
    )
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for OAuth redirect callbacks",
    )
    email_verification_expire_hours: int = Field(
        default=24, description="Email verification token TTL in hours"
    )
    password_reset_expire_hours: int = Field(
        default=1, description="Password reset token TTL in hours"
    )

    # -------------------------------------------------------------------------
    # LLM (Copilot) Configuration
    # -------------------------------------------------------------------------
    # When `copilot_llm_enabled` is False (default) the Copilot uses the
    # keyword-classifier templates in `services/agents/copilot_agent.py`
    # — fast, deterministic, free. When True, the same classifier still
    # runs (to produce intent + suggestions + data cards) but the
    # response *message text* is generated by Anthropic Claude using the
    # tenant's live metrics as context. On any LLM error (missing key,
    # network, rate limit) we silently fall back to the template path.
    copilot_llm_enabled: bool = Field(
        default=False,
        description="Route Copilot responses through Anthropic Claude when True",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key — required when copilot_llm_enabled=True",
    )
    copilot_llm_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Anthropic model id for Copilot completions",
    )
    copilot_llm_max_tokens: int = Field(
        default=600,
        description="Max output tokens per Copilot LLM call",
    )
    copilot_llm_timeout_seconds: float = Field(
        default=8.0,
        description="Hard timeout per Copilot LLM call before falling back to templates",
    )

    # -------------------------------------------------------------------------
    # Copilot RAG (PR1: indexing only — bridge wiring lands in PR2)
    # -------------------------------------------------------------------------
    copilot_rag_enabled: bool = Field(
        default=False,
        description="Retrieve relevant Stratum docs and inject into the Copilot prompt",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI key — required when copilot_rag_enabled=True (text-embedding-3-small)",
    )
    copilot_rag_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model. 1536-dim, must match the migration's vector(1536) column",
    )
    copilot_rag_top_k: int = Field(
        default=4,
        description="How many doc chunks to retrieve per query before sending to Claude",
    )
    copilot_rag_chunk_chars: int = Field(
        default=1200,
        description="Target characters per chunk during indexing (paragraph-boundary aware)",
    )

    # -------------------------------------------------------------------------
    # Stripe Payments Configuration
    # -------------------------------------------------------------------------
    stripe_secret_key: Optional[str] = Field(
        default=None, description="Stripe secret API key"
    )
    stripe_publishable_key: Optional[str] = Field(
        default=None, description="Stripe publishable key"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default=None, description="Stripe webhook signing secret"
    )
    stripe_starter_price_id: Optional[str] = Field(
        default=None, description="Stripe Price ID for Starter tier"
    )
    stripe_professional_price_id: Optional[str] = Field(
        default=None, description="Stripe Price ID for Professional tier"
    )
    stripe_enterprise_price_id: Optional[str] = Field(
        default=None, description="Stripe Price ID for Enterprise tier"
    )

    # -------------------------------------------------------------------------
    # Asset / object storage (INF-001)
    # -------------------------------------------------------------------------
    # Where uploaded creative assets are persisted. "local" writes to
    # asset_upload_dir (only durable if that path is a mounted volume);
    # "s3" streams to an S3-compatible bucket (AWS S3 or Cloudflare R2) so
    # assets survive container restarts/redeploys on Railway.
    asset_storage_backend: str = Field(
        default="local",
        description='Object storage backend for uploads: "local" or "s3"',
    )
    asset_upload_dir: str = Field(
        default="uploads/assets",
        description="Local filesystem dir for the 'local' backend (mount a volume here on Railway)",
    )
    asset_s3_bucket: Optional[str] = Field(
        default=None, description="Bucket name for the 's3' backend"
    )
    asset_s3_endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom S3 endpoint (set for Cloudflare R2; leave unset for AWS S3)",
    )
    asset_s3_region: str = Field(
        default="auto", description="S3 region ('auto' for R2)"
    )
    asset_s3_access_key: Optional[str] = Field(default=None)
    asset_s3_secret_key: Optional[str] = Field(default=None)
    asset_s3_public_base_url: Optional[str] = Field(
        default=None,
        description="Public base URL for stored objects (CDN/R2 public domain). "
        "When set, a stable public URL is returned instead of a presigned one.",
    )

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_burst: int = Field(default=20)

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    # Competitor Intelligence and Automation Rules are shelved off for launch:
    # the competitor refresh worker fabricates benchmarks with random.randint
    # and the rules beat crashes on a schema mismatch (rule.conditions). Both
    # the beat entries and the API routers are gated on these flags, so
    # flipping either True re-enables the whole surface. Turn back on only once
    # the worker uses a real data source / the rules schema is reconciled.
    feature_competitor_intel: bool = Field(default=False)
    feature_what_if_simulator: bool = Field(default=True)
    feature_automation_rules: bool = Field(default=False)
    feature_gdpr_compliance: bool = Field(default=True)
    # Knowledge Graph requires the Apache AGE Postgres extension (not
    # provisioned in the default image); shelved off by default until AGE is
    # available. (Restored: lost in a #307/#308 merge while knowledge_graph.py
    # still references it — its absence 500s every KG route.)
    feature_knowledge_graph: bool = Field(default=False)
    # Campaign-builder connector beat tasks (ad-account sync, token refresh,
    # health checks) hit live platform APIs — opt-in, default off (P1-2).
    enable_campaign_builder_beat: bool = Field(default=False)
    # Newsletter scheduled-send sweep dispatches campaigns whose scheduled_at
    # has arrived — it sends live email, so the beat is opt-in, default off.
    # (The manual send endpoint works independently once the task module is
    # registered in the Celery include.)
    enable_newsletter_beat: bool = Field(default=False)
    # Drip campaigns have no execution engine (no drip Celery task exists;
    # activate flips a flag and manual_trigger writes a "simulated" record) —
    # shelved off for launch; the whole /drip-campaigns router returns 503.
    feature_drip_campaigns: bool = Field(default=False)
    # Campaign publish marks a draft PUBLISHED with no platform call and no
    # platform_campaign_id (hardcoded SUCCESS, dispatch commented out) — a
    # data-integrity risk. Gated off until a real publish adapter lands; only
    # the publish endpoint is 503'd, draft CRUD stays available.
    enable_campaign_publish: bool = Field(default=False)

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
        default_sync = "postgresql://stratum:password@localhost:5432/stratum_ai"
        if self.database_url_sync == default_sync and self.database_url != (
            "postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai"
        ):
            # DATABASE_URL was overridden (e.g. by Railway) but DATABASE_URL_SYNC was not
            sync_url = self.database_url.replace(
                "postgresql+asyncpg://", "postgresql://", 1
            )
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
                    f"characters long (current length: {len(value)})",
                    stacklevel=2,
                )

        # --- Weak pattern detection in secret_key ---
        weak_patterns = ["dev", "changeme", "test", "placeholder", "insecure"]
        for pattern in weak_patterns:
            if pattern in self.secret_key.lower():
                warnings.warn(
                    f"SECURITY WARNING: SECRET_KEY contains weak pattern '{pattern}'. "
                    "Use a strong random key in production.",
                    stacklevel=2,
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
                    "Use a strong password in production.",
                    stacklevel=2,
                )

        return self

    @model_validator(mode="after")
    def enforce_production_safety(self) -> "Settings":
        """Reject insecure default values in production and staging environments."""
        if self.app_env in ("production", "staging"):
            if self.secret_key.startswith("dev-autogen-"):
                raise ValueError(
                    f"SECRET_KEY must be explicitly set in {self.app_env} (do not rely on auto-generated dev defaults)"
                )
            if self.jwt_secret_key.startswith("jwt-autogen-"):
                raise ValueError(
                    f"JWT_SECRET_KEY must be explicitly set in {self.app_env} (do not rely on auto-generated dev defaults)"
                )
            # PII key: reject both the old hardcoded default and auto-generated ones
            if self.pii_encryption_key == _DEV_PII_KEY:
                raise ValueError(
                    f"PII_ENCRYPTION_KEY must be explicitly set in {self.app_env} (do not rely on auto-generated dev defaults)"
                )
            if self.whatsapp_phone_number_id and not self.whatsapp_verify_token:
                import warnings

                warnings.warn(
                    f"WHATSAPP_VERIFY_TOKEN is empty in {self.app_env} "
                    "when WHATSAPP_PHONE_NUMBER_ID is configured — WhatsApp webhooks will not be verified",
                    stacklevel=2,
                )
            if (
                self.whatsapp_verify_token == "stratum-whatsapp-verify-token"
                and self.whatsapp_phone_number_id
            ):
                import warnings

                warnings.warn(
                    f"whatsapp_verify_token should be changed from default in {self.app_env} "
                    "when WhatsApp is configured — webhooks will not be secure",
                    stacklevel=2,
                )
            if self.use_mock_ad_data is True:
                raise ValueError(
                    f"use_mock_ad_data must be False in {self.app_env} — production must use real API data"
                )

            # CORS: reject localhost, 127.0.0.1, and wildcard origins
            for origin in self.cors_origins.split(","):
                origin = origin.strip()
                if not origin:
                    continue
                lower = origin.lower()
                if "localhost" in lower or "127.0.0.1" in lower or "*" in lower:
                    raise ValueError(
                        f"CORS_ORIGINS contains insecure origin '{origin}' in {self.app_env}. "
                        "Localhost, 127.0.0.1, and wildcard (*) origins are not allowed in production/staging."
                    )

            frontend = self.frontend_url.strip().rstrip("/")
            if frontend:
                lower = frontend.lower()
                if "localhost" in lower or "127.0.0.1" in lower:
                    raise ValueError(
                        f"FRONTEND_URL ('{frontend}') must not reference localhost or 127.0.0.1 in {self.app_env}"
                    )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
