"""
Unit tests for the superadmin seeder.

Two behaviours are load-bearing and were both regressions in production:

1. The module is imported by the FastAPI lifespan (``app/main.py``). It must
   never raise ``SystemExit`` at import or call time — ``SystemExit`` derives
   from ``BaseException`` and escapes the lifespan's ``except Exception``,
   which aborts API startup for the whole platform.
2. The seeder runs on *every* API start. It must be create-only, so a
   superadmin password changed through the UI is not silently reverted (and a
   deliberately deactivated account is not re-enabled) on the next restart.
"""

import importlib

import pytest

from scripts import seed_superadmin

SUPERADMIN_ENV_KEYS = (
    "SUPERADMIN_EMAIL",
    "SUPERADMIN_PASSWORD",
    "SUPERADMIN_NAME",
    "SUPERADMIN_TENANT_NAME",
    "SUPERADMIN_TENANT_SLUG",
    "SUPERADMIN_FORCE_RESET",
)

VALID_PASSWORD = "a-sufficiently-long-password"


@pytest.fixture
def clean_env(monkeypatch):
    """Remove every SUPERADMIN_* var so each test starts from a known state."""
    for key in SUPERADMIN_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


# =============================================================================
# Import safety (regression: SystemExit aborted API startup)
# =============================================================================


@pytest.mark.unit
def test_import_without_credentials_does_not_exit(clean_env):
    """Importing the seeder unconfigured must not raise SystemExit."""
    try:
        importlib.reload(seed_superadmin)
    except SystemExit as exc:  # pragma: no cover - the regression itself
        pytest.fail(f"seed_superadmin raised SystemExit at import: {exc}")


@pytest.mark.unit
def test_config_error_is_catchable_as_exception():
    """The config error must be catchable by a plain `except Exception`."""
    assert issubclass(seed_superadmin.SuperadminConfigError, Exception)
    assert not issubclass(seed_superadmin.SuperadminConfigError, SystemExit)


# =============================================================================
# load_config()
# =============================================================================


@pytest.mark.unit
def test_load_config_returns_none_when_unset(clean_env):
    assert seed_superadmin.load_config() is None


@pytest.mark.unit
def test_load_config_treats_empty_strings_as_unset(clean_env):
    """docker-compose passes ``SUPERADMIN_EMAIL=${SUPERADMIN_EMAIL:-}``.

    An absent key therefore arrives as an empty string, not as absent.
    """
    clean_env.setenv("SUPERADMIN_EMAIL", "")
    clean_env.setenv("SUPERADMIN_PASSWORD", "   ")
    assert seed_superadmin.load_config() is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("admin@example.com", ""),
        ("", VALID_PASSWORD),
    ],
)
def test_load_config_rejects_partial_config(clean_env, email, password):
    clean_env.setenv("SUPERADMIN_EMAIL", email)
    clean_env.setenv("SUPERADMIN_PASSWORD", password)
    with pytest.raises(seed_superadmin.SuperadminConfigError):
        seed_superadmin.load_config()


@pytest.mark.unit
def test_load_config_rejects_short_password(clean_env):
    clean_env.setenv("SUPERADMIN_EMAIL", "admin@example.com")
    clean_env.setenv("SUPERADMIN_PASSWORD", "x" * (seed_superadmin.MIN_PASSWORD_LENGTH - 1))
    with pytest.raises(seed_superadmin.SuperadminConfigError):
        seed_superadmin.load_config()


@pytest.mark.unit
def test_load_config_applies_defaults(clean_env):
    clean_env.setenv("SUPERADMIN_EMAIL", "admin@example.com")
    clean_env.setenv("SUPERADMIN_PASSWORD", VALID_PASSWORD)

    config = seed_superadmin.load_config()

    assert config == {
        "email": "admin@example.com",
        "password": VALID_PASSWORD,
        "name": "Platform Super Admin",
        "tenant_name": "Stratum Platform",
        "tenant_slug": "stratum-platform",
    }


@pytest.mark.unit
def test_load_config_honours_overrides(clean_env):
    clean_env.setenv("SUPERADMIN_EMAIL", "  admin@example.com  ")
    clean_env.setenv("SUPERADMIN_PASSWORD", VALID_PASSWORD)
    clean_env.setenv("SUPERADMIN_NAME", "Ops Root")
    clean_env.setenv("SUPERADMIN_TENANT_SLUG", "ops-platform")

    config = seed_superadmin.load_config()

    assert config["email"] == "admin@example.com"  # whitespace stripped
    assert config["name"] == "Ops Root"
    assert config["tenant_slug"] == "ops-platform"


# =============================================================================
# force_reset_requested()
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
def test_force_reset_truthy(clean_env, value):
    clean_env.setenv("SUPERADMIN_FORCE_RESET", value)
    assert seed_superadmin.force_reset_requested() is True


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", "false", "0", "no", "off", "maybe"])
def test_force_reset_falsy(clean_env, value):
    clean_env.setenv("SUPERADMIN_FORCE_RESET", value)
    assert seed_superadmin.force_reset_requested() is False


@pytest.mark.unit
def test_force_reset_defaults_to_false(clean_env):
    """The default must be False: seeding runs on every API start."""
    assert seed_superadmin.force_reset_requested() is False


# =============================================================================
# create_superadmin()
# =============================================================================


@pytest.mark.unit
async def test_create_superadmin_skips_without_config(clean_env):
    """Unconfigured seeding is a no-op that never opens a DB connection."""

    def fail_if_called(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("create_async_engine called despite missing config")

    clean_env.setattr(seed_superadmin, "create_async_engine", fail_if_called)

    await seed_superadmin.create_superadmin()


@pytest.mark.unit
async def test_create_superadmin_raises_catchable_error_on_bad_config(clean_env):
    """An invalid config surfaces as Exception, not SystemExit."""
    clean_env.setenv("SUPERADMIN_EMAIL", "admin@example.com")
    clean_env.setenv("SUPERADMIN_PASSWORD", "too-short")

    def fail_if_called(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("create_async_engine called despite invalid config")

    clean_env.setattr(seed_superadmin, "create_async_engine", fail_if_called)

    with pytest.raises(seed_superadmin.SuperadminConfigError):
        await seed_superadmin.create_superadmin()
