# =============================================================================
# Stratum AI - Worker PII DEK-cache bootstrap tests [AUTH-05]
# =============================================================================
"""The Celery worker_process_init handler must preload the per-tenant DEK
cache (like the API lifespan does) and must never block worker startup."""

import weakref
from unittest.mock import AsyncMock, patch

from celery.signals import worker_process_init

from app.workers.celery_app import _init_worker_pii_dek_cache


class TestWorkerPiiDekBootstrap:
    def test_handler_is_connected_to_worker_process_init(self):
        names = []
        for _key, ref in worker_process_init.receivers:  # type: ignore[attr-defined]
            fn = ref() if isinstance(ref, weakref.ReferenceType) else ref
            names.append(getattr(fn, "__name__", ""))
        assert "_init_worker_pii_dek_cache" in names

    def test_handler_initializes_dek_cache(self):
        init = AsyncMock(return_value={"loaded": 3, "provisioned": 1})
        with (
            patch("app.core.pii_keys.initialize_pii_keys", init),
            patch("app.db.session.async_session_factory") as factory,
            patch("app.db.session.dispose_stale_async_pool", AsyncMock()) as dispose,
            patch("app.db.session.async_engine") as engine,
        ):
            engine.dispose = AsyncMock()
            factory.return_value.__aenter__ = AsyncMock(return_value="session")
            factory.return_value.__aexit__ = AsyncMock(return_value=False)

            _init_worker_pii_dek_cache()

        init.assert_awaited_once_with("session")
        dispose.assert_awaited_once()  # stale-pool guard before DB use
        engine.dispose.assert_awaited_once()  # no loop-bound connections leak

    def test_handler_swallows_init_failure(self):
        boom = AsyncMock(side_effect=RuntimeError("key store down"))
        with (
            patch("app.core.pii_keys.initialize_pii_keys", boom),
            patch("app.db.session.dispose_stale_async_pool", AsyncMock()),
        ):
            # Must not raise — a key-store hiccup must not block worker startup.
            _init_worker_pii_dek_cache()
