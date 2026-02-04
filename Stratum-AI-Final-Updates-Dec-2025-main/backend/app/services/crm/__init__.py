# =============================================================================
# Stratum AI - CRM Services Package
# =============================================================================
"""
CRM integration services for HubSpot, Salesforce, Pipedrive, Zoho, etc.
"""

from app.services.crm.hubspot_client import HubSpotClient
from app.services.crm.hubspot_sync import HubSpotSyncService
from app.services.crm.hubspot_writeback import HubSpotWritebackService
from app.services.crm.identity_matching import IdentityMatcher
from app.services.crm.pipedrive_client import PipedriveClient
from app.services.crm.pipedrive_sync import PipedriveSyncService
from app.services.crm.pipedrive_writeback import PipedriveWritebackService
from app.services.crm.salesforce_client import SalesforceClient
from app.services.crm.salesforce_sync import SalesforceSyncService
from app.services.crm.salesforce_writeback import SalesforceWritebackService

__all__ = [
    "HubSpotClient",
    "HubSpotSyncService",
    "HubSpotWritebackService",
    "PipedriveClient",
    "PipedriveSyncService",
    "PipedriveWritebackService",
    "SalesforceClient",
    "SalesforceSyncService",
    "SalesforceWritebackService",
    "IdentityMatcher",
]
