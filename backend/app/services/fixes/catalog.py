"""
EMQ Fix Catalog
Maps issue codes to actions and their metadata.
"""

FIX_CATALOG = {
    "LOW_SUCCESS_RATE": {
        "one_click": True,
        "action": "enable_retries",
        "requires_role": "admin",
        "description": "API success rate dropped. Enable/strengthen retry policy.",
        "impact": "Reduces failed events by retrying with backoff",
        "roas_impact": {
            "min_pct": 5,
            "max_pct": 15,
            "avg_pct": 10,
            "confidence": "high",
            "reasoning": "Failed events = lost conversions. Retries recover 80-95% of transient failures, directly increasing attributed conversions and ROAS.",
        },
    },
    "LOW_MATCH_SCORE": {
        "one_click": True,
        "action": "set_normalization_v2",
        "requires_role": "admin",
        "description": "Coverage score dropped. Enforce stronger normalization/hashing policy.",
        "impact": "Improves EMQ by standardizing email/phone formatting",
        "roas_impact": {
            "min_pct": 10,
            "max_pct": 25,
            "avg_pct": 15,
            "confidence": "high",
            "reasoning": "Higher EMQ = better user matching = improved ad optimization. Meta's algorithm gets cleaner signals, reducing CPA by 10-20% and boosting ROAS.",
        },
    },
    "HIGH_DUPLICATES": {
        "one_click": True,
        "action": "enforce_event_id",
        "requires_role": "admin",
        "description": "Duplicate event_id detected. Enforce server-side event_id generation + strict dedupe.",
        "impact": "Eliminates duplicate events sent to Meta",
        "roas_impact": {
            "min_pct": 3,
            "max_pct": 12,
            "avg_pct": 7,
            "confidence": "medium",
            "reasoning": "Duplicates inflate conversion counts, causing Meta to over-optimize. Accurate counts lead to better bid strategies and sustainable ROAS improvement.",
        },
    },
    "LOW_EMAIL_COVERAGE": {
        "one_click": False,
        "action": "guided_email_fix",
        "requires_role": "admin",
        "description": "Email coverage is low. Requires frontend/form changes.",
        "guided_steps": [
            "Ensure email field is captured on forms before conversion events",
            "Hash emails with SHA256 before sending to CAPI",
            "Use normalized lowercase email format",
            "Check if consent is blocking email collection",
        ],
        "roas_impact": {
            "min_pct": 15,
            "max_pct": 35,
            "avg_pct": 25,
            "confidence": "high",
            "reasoning": "Email is the #1 matching signal (30+ EMQ points). High email coverage dramatically improves match rates, attribution accuracy, and ROAS.",
        },
    },
    "LOW_PHONE_COVERAGE": {
        "one_click": False,
        "action": "guided_phone_fix",
        "requires_role": "admin",
        "description": "Phone coverage is low. Requires frontend/form changes.",
        "guided_steps": [
            "Add phone number field to conversion forms",
            "Normalize to E.164 format before hashing",
            "Hash with SHA256 before sending to CAPI",
            "Consider making phone optional but encouraged",
        ],
        "roas_impact": {
            "min_pct": 8,
            "max_pct": 20,
            "avg_pct": 12,
            "confidence": "medium",
            "reasoning": "Phone is a strong secondary signal (20 EMQ points). Improves cross-device matching and attribution for mobile-heavy audiences.",
        },
    },
    "LOW_COOKIE_COVERAGE": {
        "one_click": False,
        "action": "guided_cookie_fix",
        "requires_role": "admin",
        "description": "Browser cookie (_fbp/_fbc) coverage is low. Requires website changes.",
        "guided_steps": [
            "Ensure Meta Pixel is installed and firing on all pages",
            "Read _fbp cookie value and include in CAPI events",
            "Capture fbclid from URL query params and store as _fbc",
            "Check Consent Mode - is analytics_storage denied?",
            "Verify cookies are not blocked by privacy extensions",
        ],
        "roas_impact": {
            "min_pct": 10,
            "max_pct": 30,
            "avg_pct": 18,
            "confidence": "high",
            "reasoning": "Browser cookies enable click-through attribution and deduplication. Missing _fbp/_fbc causes attribution gaps, especially for retargeting campaigns.",
        },
    },
    "MISSING_IP_UA": {
        "one_click": True,
        "action": "enable_proxy_headers",
        "requires_role": "admin",
        "description": "Client IP or User Agent missing. Enable proxy header extraction.",
        "impact": "Captures IP/UA from X-Forwarded-For and User-Agent headers",
        "roas_impact": {
            "min_pct": 5,
            "max_pct": 12,
            "avg_pct": 8,
            "confidence": "medium",
            "reasoning": "IP and User-Agent help with probabilistic matching when cookies are blocked. Improves match rates for privacy-conscious users.",
        },
    },
    "CLIENT_ID_DROP_GA4": {
        "one_click": False,
        "action": "guided_client_id_fix",
        "requires_role": "admin",
        "description": "GA4 client_id coverage dropped (cookie/consent/GTM). Guided fix steps required.",
        "guided_steps": [
            "Check Consent Mode / CMP: is analytics storage denied?",
            "Ensure GA4 config tag fires before your tracking calls",
            "Confirm _ga cookie exists and is not blocked",
            "Verify GTM container is loading correctly",
        ],
        "roas_impact": {
            "min_pct": 5,
            "max_pct": 15,
            "avg_pct": 10,
            "confidence": "medium",
            "reasoning": "GA4 client_id enables cross-session attribution and audience building. Missing IDs break remarketing and reduce campaign effectiveness.",
        },
    },
    "CONFIG_MISMATCH": {
        "one_click": True,
        "action": "reset_config",
        "requires_role": "admin",
        "description": "Configuration appears misconfigured. Reset to recommended defaults.",
        "impact": "Resets retry, normalization, and dedupe settings to optimal values",
        "roas_impact": {
            "min_pct": 10,
            "max_pct": 30,
            "avg_pct": 20,
            "confidence": "medium",
            "reasoning": "Misconfigured settings compound multiple issues. A full reset often resolves hidden problems affecting event quality and attribution.",
        },
    },
}


def get_fix_metadata(issue_code: str) -> dict | None:
    """Get metadata for a fix by issue code."""
    return FIX_CATALOG.get(issue_code)


def get_all_one_click_fixes() -> list[str]:
    """Get list of all one-click fixable issue codes."""
    return [code for code, meta in FIX_CATALOG.items() if meta.get("one_click")]


def get_all_guided_fixes() -> list[str]:
    """Get list of all guided fix issue codes."""
    return [code for code, meta in FIX_CATALOG.items() if not meta.get("one_click")]
