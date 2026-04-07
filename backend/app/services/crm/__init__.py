# =============================================================================
# Stratum AI - CRM Services Package
# =============================================================================
"""
CRM integration services for HubSpot, Salesforce, etc.
"""

from app.services.crm.hubspot_client import HubSpotClient
from app.services.crm.hubspot_sync import HubSpotSyncService
from app.services.crm.identity_matching import IdentityMatcher

__all__ = [
    "HubSpotClient",
    "HubSpotSyncService",
    "IdentityMatcher",
]
