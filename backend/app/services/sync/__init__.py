# =============================================================================
# Stratum AI - Platform Sync Services
# =============================================================================
"""
Services for syncing campaign data from ad platforms (Meta, TikTok).

Modules:
- meta_sync: Meta Marketing API campaign and insights sync
- tiktok_sync: TikTok Marketing API campaign and report sync
- orchestrator: Coordinates sync across platforms and tenants
"""

from app.services.sync.meta_sync import MetaCampaignSyncService
from app.services.sync.orchestrator import PlatformSyncOrchestrator, SyncResult
from app.services.sync.tiktok_sync import TikTokCampaignSyncService

__all__ = [
    "MetaCampaignSyncService",
    "TikTokCampaignSyncService",
    "PlatformSyncOrchestrator",
    "SyncResult",
]
