# =============================================================================
# Stratum AI - Integration Config Startup Check Tests
# =============================================================================
"""
Guards the startup check that catches integrations which look configured
but cannot work.

Every case here is a real defect this codebase shipped:

  * TIKTOK_APP_SECRET  — field is `tiktok_secret`
  * GOOGLE_CLIENT_ID   — field is `google_ads_client_id`
  * COPILOT_LLM_ENABLED=true with no ANTHROPIC_API_KEY
  * COPILOT_LLM_MODEL truncated to `claude-haiku-4-5-20251`
  * Half-configured connectors that fail at first use, not at startup

The last test is the important one: production's real configuration must
still boot. A config linter that refuses to start the API is worse than
the bugs it catches.
"""

import os
import warnings

import pytest

from app.core.config import Settings

# Prefixes the check owns — cleared between cases so a developer's real
# environment cannot leak into an assertion.
_OWNED = (
    "TIKTOK_",
    "GOOGLE_",
    "META_",
    "WHATSAPP_",
    "COPILOT_",
    "ANTHROPIC_",
    "OPENAI_",
    "STRIPE_",
    "SNAPCHAT_",
    "HUBSPOT_",
    "PIPEDRIVE_",
    "ALERT_",
)

_PROD_BASE = {
    "APP_ENV": "production",
    "SECRET_KEY": "x" * 40,
    "JWT_SECRET_KEY": "y" * 40,
    "PII_ENCRYPTION_KEY": "z" * 40,
    "METRICS_API_KEY": "m" * 20,
    "CORS_ORIGINS": "https://app.stratumai.app",
    "FRONTEND_URL": "https://app.stratumai.app",
    "USE_MOCK_AD_DATA": "false",
    "DATABASE_URL": "postgresql+asyncpg://u:p@db:5432/s",
}


@pytest.fixture
def clean_env(monkeypatch):
    """Strip owned prefixes so the host environment cannot affect results."""
    for key in list(os.environ):
        if key.startswith(_OWNED):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch


def _warnings_from(env, monkeypatch):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Settings()
        return [str(w.message) for w in caught]


class TestUnreadEnvVars:
    """Vars bound to no setting are silently dropped by extra="ignore"."""

    def test_misspelled_tiktok_secret_is_flagged_with_suggestion(self, clean_env):
        msgs = _warnings_from({"TIKTOK_APP_SECRET": "s"}, clean_env)
        unread = [m for m in msgs if "UNREAD ENV VARS" in m]

        assert unread, "TIKTOK_APP_SECRET should be reported as unread"
        assert "TIKTOK_APP_SECRET is ignored" in unread[0]
        assert "did you mean TIKTOK_SECRET?" in unread[0]

    def test_google_without_ads_prefix_is_flagged(self, clean_env):
        """The real bug: GOOGLE_CLIENT_ID, not GOOGLE_ADS_CLIENT_ID."""
        msgs = _warnings_from({"GOOGLE_CLIENT_ID": "c"}, clean_env)
        unread = [m for m in msgs if "UNREAD ENV VARS" in m]

        assert unread
        assert "did you mean GOOGLE_ADS_CLIENT_ID?" in unread[0]

    def test_infra_vars_are_not_flagged(self, clean_env):
        """POSTGRES_/GRAFANA_/R2_ belong to other services, not Settings."""
        msgs = _warnings_from(
            {
                "POSTGRES_PASSWORD": "p",
                "GRAFANA_ADMIN_USER": "g",
                "R2_BUCKET": "b",
                "REDIS_PASSWORD": "r",
            },
            clean_env,
        )

        assert not [m for m in msgs if "UNREAD ENV VARS" in m]

    def test_correctly_named_var_is_not_flagged(self, clean_env):
        msgs = _warnings_from({"TIKTOK_SECRET": "s"}, clean_env)

        assert not [m for m in msgs if "UNREAD ENV VARS" in m]


class TestHalfConfiguredIntegrations:
    """One credential set and its partner missing fails at first use."""

    def test_meta_missing_secret_warns_in_development(self, clean_env):
        msgs = _warnings_from({"META_APP_ID": "abc"}, clean_env)
        problems = [m for m in msgs if "INTEGRATION CONFIG" in m]

        assert problems
        assert "Meta is partially configured" in problems[0]
        assert "META_APP_SECRET" in problems[0]

    def test_meta_missing_secret_refuses_to_boot_in_production(self, clean_env):
        for k, v in {**_PROD_BASE, "META_APP_ID": "abc"}.items():
            clean_env.setenv(k, v)

        with pytest.raises(ValueError) as exc:
            Settings()

        assert "Meta is partially configured" in str(exc.value)

    def test_fully_unconfigured_integration_is_silent(self, clean_env):
        """Not using an integration is not a misconfiguration."""
        msgs = _warnings_from({"META_APP_ID": "", "META_APP_SECRET": ""}, clean_env)

        assert not [m for m in msgs if "INTEGRATION CONFIG" in m]

    def test_whatsapp_only_triggers_on_phone_number_id(self, clean_env):
        """A verify token alone is prod's real state — must stay silent."""
        msgs = _warnings_from({"WHATSAPP_VERIFY_TOKEN": "v" * 48}, clean_env)

        assert not [m for m in msgs if "INTEGRATION CONFIG" in m]

    def test_whatsapp_with_phone_number_demands_the_rest(self, clean_env):
        msgs = _warnings_from({"WHATSAPP_PHONE_NUMBER_ID": "123"}, clean_env)
        problems = [m for m in msgs if "INTEGRATION CONFIG" in m]

        assert problems
        assert "WHATSAPP_APP_SECRET" in problems[0]


class TestFeatureFlagDependencies:
    """A flag switched on without its credential fails silently at runtime."""

    def test_llm_enabled_without_key_is_flagged(self, clean_env):
        msgs = _warnings_from({"COPILOT_LLM_ENABLED": "true"}, clean_env)
        problems = [m for m in msgs if "INTEGRATION CONFIG" in m]

        assert problems
        assert "ANTHROPIC_API_KEY is unset" in problems[0]

    def test_rag_enabled_without_key_is_flagged(self, clean_env):
        msgs = _warnings_from(
            {"COPILOT_RAG_ENABLED": "true", "OPENAI_API_KEY": ""}, clean_env
        )
        problems = [m for m in msgs if "INTEGRATION CONFIG" in m]

        assert problems
        assert "OPENAI_API_KEY is unset" in problems[0]


class TestTruncatedModelId:
    """The failure that looks most like success: wrong model, silent fallback."""

    def test_truncated_model_id_is_detected(self, clean_env):
        msgs = _warnings_from(
            {
                "COPILOT_LLM_ENABLED": "true",
                "ANTHROPIC_API_KEY": "k" * 100,
                "COPILOT_LLM_MODEL": "claude-haiku-4-5-20251",
            },
            clean_env,
        )
        problems = [m for m in msgs if "INTEGRATION CONFIG" in m]

        assert problems
        assert "looks truncated" in problems[0]

    def test_complete_model_id_is_silent(self, clean_env):
        msgs = _warnings_from(
            {
                "COPILOT_LLM_ENABLED": "true",
                "ANTHROPIC_API_KEY": "k" * 100,
                "COPILOT_LLM_MODEL": "claude-haiku-4-5-20251001",
            },
            clean_env,
        )

        assert not [m for m in msgs if "INTEGRATION CONFIG" in m]


class TestProductionMustStillBoot:
    """The guard on the guard.

    Production's actual configuration as of 2026-08-24: Copilot LLM on,
    alert webhook set, every ad platform and Stripe empty, WhatsApp holding
    only a verify token. This must construct cleanly and silently. A config
    check that refuses to start the API is worse than the bugs it catches.
    """

    def test_current_production_config_boots_without_complaint(self, clean_env):
        env = {
            **_PROD_BASE,
            "META_APP_ID": "",
            "META_APP_SECRET": "",
            "SNAPCHAT_CLIENT_ID": "",
            "SNAPCHAT_CLIENT_SECRET": "",
            "TIKTOK_APP_ID": "",
            "TIKTOK_SECRET": "",
            "GOOGLE_ADS_CLIENT_ID": "",
            "GOOGLE_ADS_CLIENT_SECRET": "",
            "GOOGLE_ADS_DEVELOPER_TOKEN": "",
            "STRIPE_SECRET_KEY": "",
            "STRIPE_WEBHOOK_SECRET": "",
            "WHATSAPP_VERIFY_TOKEN": "v" * 48,
            "ANTHROPIC_API_KEY": "k" * 108,
            "COPILOT_LLM_ENABLED": "true",
            "COPILOT_LLM_MODEL": "claude-haiku-4-5-20251001",
            "ALERT_WEBHOOK_URL": "https://hooks.slack.com/services/" + "a" * 48,
        }
        msgs = _warnings_from(env, clean_env)

        assert not [m for m in msgs if "INTEGRATION CONFIG" in m]
        assert not [m for m in msgs if "UNREAD ENV VARS" in m]
