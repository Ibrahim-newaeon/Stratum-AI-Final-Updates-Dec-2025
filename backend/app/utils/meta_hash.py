# =============================================================================
# Stratum AI - Meta CAPI Hashing Utilities
# =============================================================================
"""
Normalization and SHA-256 hashing for Meta CAPI PII fields.
"""

import hashlib
import re


def _sha256(s: str) -> str:
    """SHA-256 hash a string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def norm_email(v: str) -> str:
    """Normalize email: lowercase, trim whitespace."""
    return v.strip().lower()


def norm_phone(v: str) -> str:
    """Normalize phone: digits only (ensure E.164 upstream)."""
    return re.sub(r"[^\d]", "", v.strip())


def norm_text(v: str) -> str:
    """Normalize generic text: lowercase, trim whitespace."""
    return v.strip().lower()


def hash_email(v: str | None) -> str | None:
    """Normalize and hash email."""
    if not v:
        return None
    x = norm_email(v)
    return _sha256(x) if x else None


def hash_phone(v: str | None) -> str | None:
    """Normalize and hash phone."""
    if not v:
        return None
    x = norm_phone(v)
    return _sha256(x) if x else None


def hash_text(v: str | None) -> str | None:
    """Normalize and hash generic text (name, city, etc.)."""
    if not v:
        return None
    x = norm_text(v)
    return _sha256(x) if x else None
