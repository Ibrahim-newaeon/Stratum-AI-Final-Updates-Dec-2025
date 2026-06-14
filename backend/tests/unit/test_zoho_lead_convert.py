# =============================================================================
# Stratum AI - Zoho Lead->Contact Conversion Unit Tests
# =============================================================================
"""Unit tests for the pure ``ZohoSyncService._convert_lead_to_contact``
transform in ``app.services.crm.zoho_sync`` — reshaping a Zoho lead record
into the contact format the upsert path expects. The DB-backed sync
pipeline is out of scope here.
"""

import pytest

from app.services.crm.zoho_sync import ZohoSyncService

pytestmark = pytest.mark.unit


@pytest.fixture
def service() -> ZohoSyncService:
    # __init__ only stores db/tenant and constructs light helpers; no I/O.
    return ZohoSyncService(db=None, tenant_id=1)


class TestConvertLeadToContact:
    def test_prefixes_id_and_marks_lifecycle(self, service):
        out = service._convert_lead_to_contact({"id": "42", "Lead_Status": "New"})
        assert out["id"] == "lead_42"
        assert out["_lifecycle_stage"] == "lead"
        assert out["_lead_status"] == "New"

    def test_company_wrapped_as_account_object(self, service):
        out = service._convert_lead_to_contact({"id": "1", "Company": "Acme Inc"})
        # Company is nested under Account_Name so normalize_zoho_contact can flatten it.
        assert out["Account_Name"] == {"name": "Acme Inc"}

    def test_maps_identity_and_passthrough_fields(self, service):
        out = service._convert_lead_to_contact(
            {
                "id": "9",
                "Email": "lead@example.com",
                "Phone": "555",
                "First_Name": "Ada",
                "Last_Name": "Byte",
                "Lead_Source": "Webinar",
            }
        )
        assert out["Email"] == "lead@example.com"
        assert out["Phone"] == "555"
        assert out["First_Name"] == "Ada"
        assert out["Last_Name"] == "Byte"
        assert out["Lead_Source"] == "Webinar"

    def test_missing_fields_default_to_none(self, service):
        out = service._convert_lead_to_contact({"id": "3"})
        assert out["Email"] is None
        assert out["Account_Name"] == {"name": None}
