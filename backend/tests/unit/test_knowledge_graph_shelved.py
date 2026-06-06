# =============================================================================
# Stratum AI - Knowledge Graph Shelving Tests
# =============================================================================
"""
Tests for shelving the Knowledge Graph behind a feature flag (P1-6).

The KG depends on the Apache AGE Postgres extension, which is not
provisioned. The router-level gate must return 503 when the flag is off
(the default) and allow requests through when it is explicitly enabled.
"""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.knowledge_graph import require_knowledge_graph_enabled
from app.core.config import settings


async def test_disabled_by_default_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "feature_knowledge_graph", False)
    with pytest.raises(HTTPException) as exc:
        await require_knowledge_graph_enabled()
    assert exc.value.status_code == 503
    assert "AGE" in exc.value.detail


async def test_enabled_passes(monkeypatch):
    monkeypatch.setattr(settings, "feature_knowledge_graph", True)
    assert await require_knowledge_graph_enabled() is None


def test_flag_defaults_off():
    # Shipped default must be off (KG undeployable without AGE).
    assert settings.feature_knowledge_graph is False
