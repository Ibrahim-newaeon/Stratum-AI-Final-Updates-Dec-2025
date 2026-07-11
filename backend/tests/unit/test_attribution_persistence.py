# =============================================================================
# Stratum AI - Attribution Model Persistence Tests
# =============================================================================
"""
Tests for persisting trained attribution models (Tier 3).

Training used to be stateless (train-and-return), so the frontend's model
registry (list / activate / archive / results / training-runs) 404'd — nothing
was ever stored, even though the tables (`trained_attribution_models`,
`model_training_runs`) existed. Training now persists via `_build_trained_model`
and the registry CRUD endpoints read/write those tables.

These are pure/route-shape tests (no DB): the result→model mapping and that the
registry routes + `model_id` response field exist.
"""

from datetime import datetime

from app.api.v1.endpoints.data_driven_attribution import ModelTrainingResponse
from app.api.v1.endpoints.data_driven_attribution import router as dda_router
from app.models.attribution import (
    DataDrivenModelType,
    ModelStatus,
    TrainedAttributionModel,
)
from app.services.attribution.model_training import _build_trained_model


def test_build_trained_model_maps_markov_result():
    result = {
        "success": True,
        "model_name": "markov_chain_platform_2026-01-31",
        "attribution_weights": {"meta": 0.6, "google": 0.4},
        "removal_effects": {"meta": 0.5, "google": 0.3},
        "journey_count": 1200,
        "converting_journeys": 300,
        "baseline": 0.12,
    }
    m = _build_trained_model(
        tenant_id=7,
        model_type="markov_chain",
        channel_type="platform",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        result=result,
        created_by_user_id=99,
    )
    assert isinstance(m, TrainedAttributionModel)
    assert m.tenant_id == 7
    assert m.model_type == DataDrivenModelType.MARKOV_CHAIN
    assert m.status == ModelStatus.ACTIVE  # trained & available
    assert m.is_active is False  # selection is separate (activate endpoint)
    assert m.attribution_weights == {"meta": 0.6, "google": 0.4}
    assert m.removal_effects == {"meta": 0.5, "google": 0.3}
    assert m.journey_count == 1200
    assert m.converting_journeys == 300
    assert m.unique_channels == 2  # derived from weights when absent
    assert m.baseline_conversion_rate == 0.12  # from "baseline" fallback
    assert m.created_by_user_id == 99
    # datetime training window is narrowed to Date columns.
    assert m.training_start == datetime(2026, 1, 1).date()
    assert m.training_end == datetime(2026, 1, 31).date()


def test_build_trained_model_shapley():
    result = {
        "success": True,
        "model_name": "s",
        "attribution_weights": {"a": 1.0},
        "shapley_values": {"a": 0.9},
    }
    m = _build_trained_model(
        tenant_id=1,
        model_type="shapley_value",
        channel_type="campaign",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 2),
        result=result,
    )
    assert m.model_type == DataDrivenModelType.SHAPLEY_VALUE
    assert m.shapley_values == {"a": 0.9}
    assert m.channel_type == "campaign"


def test_registry_routes_registered():
    # Strip the router prefix so the assertion holds regardless of how the
    # prefix is applied.
    rel = {r.path.replace("/attribution/data-driven", "") for r in dda_router.routes}
    assert "/models" in rel
    assert "/models/{model_id}" in rel
    assert "/models/{model_id}/activate" in rel
    assert "/models/{model_id}/archive" in rel
    assert "/training-runs" in rel


def test_training_response_exposes_model_id():
    assert "model_id" in ModelTrainingResponse.model_fields
