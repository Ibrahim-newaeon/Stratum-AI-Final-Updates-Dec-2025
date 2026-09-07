# =============================================================================
# Stratum AI - Tenant-facing CRM Schemas
# =============================================================================
"""Schemas for the tenant-scoped CRM surface under ``/integrations/crm``.

Distinct from the response models inside ``api/v1/endpoints/integrations.py``,
which serve the superadmin surface: those take a ``tenant_id`` query parameter
and are guarded by ``require_super_admin``, while everything here derives the
tenant from the caller's own token.

Two deliberate omissions. The second is data that does not exist; the first is
data this surface must not carry, which is not the same thing:

* ``CRMContactRead`` exposes no email, name, phone or company. ``CRMContact``
  has no plaintext column for any of them — only ``email_hash`` and
  ``phone_hash``, SHA256 digests kept for identity matching — and the hashes are
  not useful to a UI, so neither is serialised.

  This is not the same as saying the plaintext is absent from the database.
  ``CRMContact.raw_properties`` holds HubSpot's whole property payload, which
  ``hubspot_sync`` requests with ``email``, ``phone``, ``firstname`` and
  ``lastname`` in the list. Nothing serialises it and this schema must keep it
  that way; see docs/05-operations/crm-contact-pii-decision.md, which is open.
* Deal money is ``amount_cents`` only. ``CRMDeal.amount`` is marked DEPRECATED
  in the model ("should not be used for calculations"), so exposing it would
  invite a float rounding bug in the client.
"""

from datetime import date, datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CRMConnectionRead(BaseModel):
    """A tenant's CRM connection, without any token material."""

    id: UUID
    provider: str
    status: str
    status_message: Optional[str] = None
    provider_account_id: Optional[str] = None
    provider_account_name: Optional[str] = None

    sync_contacts: bool
    sync_deals: bool
    sync_companies: bool

    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_contacts_count: Optional[int] = None
    last_sync_deals_count: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CRMContactRead(BaseModel):
    """A synced CRM contact. Identity fields are hashed and never returned."""

    id: UUID
    crm_contact_id: str
    lifecycle_stage: Optional[str] = None
    lead_source: Optional[str] = None

    first_touch_campaign_id: Optional[str] = None
    last_touch_campaign_id: Optional[str] = None
    first_touch_ts: Optional[datetime] = None
    last_touch_ts: Optional[datetime] = None
    touch_count: Optional[int] = None

    stratum_quality_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CRMDealRead(BaseModel):
    """A synced CRM deal with its attribution, valued in cents."""

    id: UUID
    crm_deal_id: str
    deal_name: Optional[str] = None
    stage: Optional[str] = None
    stage_normalized: Optional[str] = None

    amount_cents: Optional[int] = None
    currency: str

    close_date: Optional[date] = None
    expected_close_date: Optional[date] = None
    is_won: bool
    is_closed: bool
    won_at: Optional[datetime] = None

    attributed_campaign_id: Optional[str] = None
    attributed_platform: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PipelineSummaryRead(BaseModel):
    """Deal counts and values by stage for the caller's tenant."""

    status: str
    stage_counts: Dict[str, int] = Field(default_factory=dict)
    stage_values: Dict[str, float] = Field(default_factory=dict)
    total_pipeline_value: float = 0
    total_won_value: float = 0
    won_deal_count: int = 0
    last_sync_at: Optional[str] = None


class WritebackConfigRead(BaseModel):
    """Writeback settings and the outcome of the last run."""

    id: UUID
    connection_id: UUID

    enabled: bool
    sync_contacts: bool
    sync_deals: bool
    auto_sync_enabled: bool
    sync_interval_hours: int

    sync_attribution: bool
    sync_profit_metrics: bool
    sync_touchpoint_count: bool

    properties_created: bool
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_contacts: Optional[int] = None
    last_sync_deals: Optional[int] = None
    last_sync_errors: Optional[int] = None
    next_sync_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WritebackConfigUpdate(BaseModel):
    """Editable writeback settings.

    Every field is optional so a caller can PATCH-style update one toggle.
    Carries no tenant_id or connection_id: both are resolved from the
    authenticated tenant, never from the request body.
    """

    enabled: Optional[bool] = None
    sync_contacts: Optional[bool] = None
    sync_deals: Optional[bool] = None
    auto_sync_enabled: Optional[bool] = None
    # Bounded because the value feeds next_sync_at arithmetic in
    # run_scheduled_writebacks; 0 would re-dispatch on every sweep.
    sync_interval_hours: Optional[int] = Field(default=None, ge=1, le=720)
    sync_attribution: Optional[bool] = None
    sync_profit_metrics: Optional[bool] = None
    sync_touchpoint_count: Optional[bool] = None


class SyncTriggerRead(BaseModel):
    """Result of asking for a sync on one connection."""

    connection_id: UUID
    provider: str
    status: str
    contacts_synced: int = 0
    deals_synced: int = 0
    message: Optional[str] = None
