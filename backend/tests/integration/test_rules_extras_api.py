# =============================================================================
# Stratum AI - Automation Rules API Integration Tests (dry-run + executions)
# =============================================================================
"""Integration tests for the two rules endpoints not covered by
``test_rules_api.py``: ``POST /rules/{id}/test`` (dry-run evaluation) and
``GET /rules/{id}/executions`` (execution history). A rule is created via the
real create endpoint, then driven through both.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/rules"


def _rule(name="Dry-run rule", **extra):
    body = {
        "name": name,
        "description": "Pause campaigns when CPA exceeds target",
        "condition_field": "cpa",
        "condition_operator": "greater_than",
        "condition_value": "50",
        "condition_duration_hours": 24,
        "action_type": "pause_campaign",
        "action_config": {},
        "cooldown_hours": 24,
    }
    body.update(extra)
    return body


async def _create_rule(client: AsyncClient) -> int:
    resp = await client.post(_BASE, json=_rule())
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


class TestRuleDryRun:
    async def test_test_rule_dry_run(self, authenticated_client: AsyncClient):
        rule_id = await _create_rule(authenticated_client)
        resp = await authenticated_client.post(f"{_BASE}/{rule_id}/test")
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    async def test_test_unknown_rule_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"{_BASE}/99999999/test")
        assert resp.status_code == 404


class TestRuleExecutions:
    async def test_executions_empty_for_new_rule(
        self, authenticated_client: AsyncClient
    ):
        rule_id = await _create_rule(authenticated_client)
        resp = await authenticated_client.get(f"{_BASE}/{rule_id}/executions")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"] == []

    async def test_executions_unknown_rule_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/99999999/executions")
        assert resp.status_code == 404
