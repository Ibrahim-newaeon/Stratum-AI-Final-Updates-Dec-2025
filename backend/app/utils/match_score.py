# =============================================================================
# Stratum AI - Match Coverage Score Calculator
# =============================================================================
"""
Calculate Match Coverage Score based on identifier presence flags.
Weights aligned with EMQ drivers.
"""


def calc_match_coverage_score(flags: dict[str, bool]) -> float:
    """
    Calculate match coverage score from identifier presence flags.

    Weights:
    - email: 25
    - phone: 20
    - external_id: 20
    - fbp: 15
    - fbc: 10
    - ip + ua: 10 (only if BOTH present)
    - fn: 3
    - ln: 3
    - ct: 2
    - country: 2
    - zp: 2

    Returns: Score capped at 100
    """
    weights = {
        "has_em": 25,
        "has_ph": 20,
        "has_external_id": 20,
        "has_fbp": 15,
        "has_fbc": 10,
        "ip_ua": 10,  # only if both ip and ua
        "has_fn": 3,
        "has_ln": 3,
        "has_ct": 2,
        "has_country": 2,
        "has_zp": 2,
    }

    score = 0.0

    if flags.get("has_em"):
        score += weights["has_em"]
    if flags.get("has_ph"):
        score += weights["has_ph"]
    if flags.get("has_external_id"):
        score += weights["has_external_id"]
    if flags.get("has_fbp"):
        score += weights["has_fbp"]
    if flags.get("has_fbc"):
        score += weights["has_fbc"]
    if flags.get("has_ip") and flags.get("has_ua"):
        score += weights["ip_ua"]
    if flags.get("has_fn"):
        score += weights["has_fn"]
    if flags.get("has_ln"):
        score += weights["has_ln"]
    if flags.get("has_ct"):
        score += weights["has_ct"]
    if flags.get("has_country"):
        score += weights["has_country"]
    if flags.get("has_zp"):
        score += weights["has_zp"]

    return float(min(100.0, score))
