# =============================================================================
# Stratum AI - Meta CAPI Schemas
# =============================================================================
"""
Pydantic schemas for Meta Conversion API event collection.
Matches the CapiQaLog model for full identifier tracking.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal


class MetaUserIn(BaseModel):
    """User identifiers for Meta CAPI - will be normalized and hashed server-side."""

    # Core identifiers (hashed)
    email: Optional[str] = None
    phone: Optional[str] = None
    external_id: Optional[str] = None

    # Meta-specific cookies (not hashed)
    fbp: Optional[str] = None  # _fbp cookie
    fbc: Optional[str] = None  # fbclid from URL

    # Additional PII (hashed)
    fn: Optional[str] = None  # first_name
    ln: Optional[str] = None  # last_name
    ct: Optional[str] = None  # city
    country: Optional[str] = None
    zp: Optional[str] = None  # zip_code

    # Client info (not hashed)
    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None


class MetaCustomDataIn(BaseModel):
    """Custom event data for Meta CAPI."""

    value: Optional[float] = None
    currency: Optional[str] = None
    content_ids: Optional[List[str]] = None
    content_type: Optional[str] = None
    contents: Optional[List[Dict[str, Any]]] = None
    num_items: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class MetaCapiCollectIn(BaseModel):
    """
    Request schema for POST /api/events/collect

    Frontend sends raw identifiers; backend normalizes, hashes, sends to Meta, logs QA.
    """

    # Event identifiers
    event_name: str = Field(..., examples=["Lead", "Purchase", "AddToCart", "ViewContent"])
    event_time: Optional[int] = None  # Unix timestamp, defaults to now
    event_id: str = Field(..., min_length=6)  # Required for Pixel+CAPI deduplication
    action_source: Literal["website"] = "website"
    event_source_url: Optional[str] = None

    # Platform fields
    pixel_id: Optional[str] = None
    dataset_id: Optional[str] = None
    platform: str = "meta"

    # User identifiers
    user: MetaUserIn = Field(default_factory=MetaUserIn)

    # Event parameters
    custom_data: Optional[MetaCustomDataIn] = None

    # Optional: test mode
    test_event_code: Optional[str] = None


class MetaCapiCollectOut(BaseModel):
    """
    Response schema for POST /api/events/collect

    Returns QA info for frontend debugging/monitoring.
    """

    ok: bool
    qa_log_id: int
    match_coverage_score: float
    meta_success: bool
    meta_events_received: int
    meta_trace_id: Optional[str] = None
    meta_error_code: Optional[int] = None
    meta_error_message: Optional[str] = None
