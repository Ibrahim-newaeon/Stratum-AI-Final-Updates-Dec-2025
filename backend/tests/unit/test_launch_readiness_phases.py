# =============================================================================
# Stratum AI - Launch Readiness Phase Catalog (Unit Tests)
# =============================================================================
"""
Invariants for the static Launch Readiness phase catalog. These run without
a database or any framework imports.
"""

import pytest

from app.core.launch_readiness_phases import (
    LAUNCH_READINESS_PHASES,
    all_item_keys,
    find_item,
    get_phase_by_number,
    total_item_count,
)


pytestmark = pytest.mark.unit


def test_catalog_has_exactly_twelve_phases():
    assert len(LAUNCH_READINESS_PHASES) == 12


def test_phase_numbers_are_contiguous_from_one():
    numbers = [p["number"] for p in LAUNCH_READINESS_PHASES]
    assert numbers == list(range(1, 13))


def test_phase_slugs_are_unique():
    slugs = [p["slug"] for p in LAUNCH_READINESS_PHASES]
    assert len(set(slugs)) == len(slugs)


def test_phase_slugs_are_kebab_case():
    import re

    pattern = re.compile(r"^[a-z][a-z0-9-]*$")
    for phase in LAUNCH_READINESS_PHASES:
        assert pattern.match(phase["slug"]), f"bad slug: {phase['slug']}"


def test_every_phase_has_a_title_and_description():
    for phase in LAUNCH_READINESS_PHASES:
        assert phase["title"], f"phase {phase['number']} missing title"
        assert phase["description"], f"phase {phase['number']} missing description"


def test_every_phase_has_at_least_one_item():
    for phase in LAUNCH_READINESS_PHASES:
        assert len(phase["items"]) >= 1, f"phase {phase['number']} has no items"


def test_item_keys_are_globally_unique():
    keys = [item["key"] for phase in LAUNCH_READINESS_PHASES for item in phase["items"]]
    assert len(set(keys)) == len(keys)


def test_item_keys_are_snake_case():
    import re

    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for phase in LAUNCH_READINESS_PHASES:
        for item in phase["items"]:
            assert pattern.match(item["key"]), f"bad item key: {item['key']}"


def test_item_key_length_fits_column():
    # item_key column is String(100); keep a safety margin.
    for phase in LAUNCH_READINESS_PHASES:
        for item in phase["items"]:
            assert len(item["key"]) <= 100


def test_every_item_has_a_title():
    for phase in LAUNCH_READINESS_PHASES:
        for item in phase["items"]:
            assert item["title"].strip(), f"empty title for {item['key']}"


def test_total_item_count_matches_sum_of_phases():
    manual = sum(len(p["items"]) for p in LAUNCH_READINESS_PHASES)
    assert total_item_count() == manual


def test_all_item_keys_returns_every_key_with_phase_number():
    pairs = all_item_keys()
    assert len(pairs) == total_item_count()
    for phase_number, key in pairs:
        phase = get_phase_by_number(phase_number)
        assert phase is not None
        assert any(i["key"] == key for i in phase["items"])


def test_find_item_returns_phase_and_item_for_known_key():
    located = find_item("gcp_org_created")
    assert located is not None
    phase, item = located
    assert phase["number"] == 1
    assert item["key"] == "gcp_org_created"


def test_find_item_returns_none_for_unknown_key():
    assert find_item("totally_made_up_key_xyz") is None


def test_get_phase_by_number_returns_matching_phase():
    phase = get_phase_by_number(3)
    assert phase is not None
    assert phase["title"] == "Container Platform"


def test_get_phase_by_number_returns_none_for_out_of_range():
    assert get_phase_by_number(0) is None
    assert get_phase_by_number(99) is None
