# =============================================================================
# Stratum AI - Domain Package (Legacy)
# =============================================================================
# Domain models have been consolidated into app.models.
# Re-export from canonical locations for backwards compatibility.
# Do NOT define models here to avoid duplicate table registration.

from app.models.campaign_builder import (
    CampaignDraft,
    CampaignPublishLog,
    ConnectionStatus,
    DraftStatus,
    PublishResult,
    TenantAdAccount,
    TenantPlatformConnection,
)
from app.models.trust_layer import (
    AttributionVarianceStatus,
    FactActionsQueue,
    FactAttributionVarianceDaily,
    FactSignalHealthDaily,
    SignalHealthStatus,
)
