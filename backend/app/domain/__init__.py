# =============================================================================
# Stratum AI - Domain Package (Legacy)
# =============================================================================
# Domain models have been consolidated into app.models.
# Re-export from canonical locations for backwards compatibility.
# Do NOT define models here to avoid duplicate table registration.

from app.models.trust_layer import (
    FactSignalHealthDaily,
    FactAttributionVarianceDaily,
    FactActionsQueue,
    SignalHealthStatus,
    AttributionVarianceStatus,
)

from app.models.campaign_builder import (
    ConnectionStatus,
    DraftStatus,
    PublishResult,
    TenantPlatformConnection,
    TenantAdAccount,
    CampaignDraft,
    CampaignPublishLog,
)
