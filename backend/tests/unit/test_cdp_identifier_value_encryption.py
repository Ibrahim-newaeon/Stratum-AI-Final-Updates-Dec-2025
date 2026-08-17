# =============================================================================
# Stratum AI - CDP Identifier Value At Rest [CDP-04]
# =============================================================================
"""`cdp_profile_identifiers.identifier_value` is encrypted under the row's tenant.

The column held raw email addresses and phone numbers in the clear — the comment
next to it said "Original (can be redacted later)", and later never came. It sits
beside `identifier_hash`, a SHA-256 of the normalized value, which is what every
lookup actually uses; the plaintext copy existed only to be displayed back.

Unlike `CMSContactSubmission`, this table **has** a `tenant_id`, so the
prescribed pattern applies: explicit accessors that pass the owning tenant to
`encrypt_pii`, as `AudienceSyncCredential` does for platform tokens. The
global-key `EncryptedString` column type is deliberately not used here — it
cannot reach `tenant_id` from inside a `TypeDecorator`, so it would silently
drop every identifier into one shared key scheme.

The constructor no longer accepts `identifier_value=`. That is the point: a
keyword argument would be encrypted in whatever order SQLAlchemy happens to
apply kwargs, and if `tenant_id` had not been set yet the value would be
encrypted under the global key while looking completely successful. Refusing the
kwarg turns that into an immediate AttributeError instead of a silent downgrade.
"""

import pytest

from app.core.security import encrypt_pii
from app.models.cdp import CDPProfileIdentifier

pytestmark = pytest.mark.asyncio

# app/schemas/cdp.py caps IdentifierInput.value at 512 chars, so the column has
# to hold the ciphertext of a 512-char value (~2.2x + overhead here).
_MAX_INPUT = 512


def _identifier(tenant_id: int = 7) -> CDPProfileIdentifier:
    return CDPProfileIdentifier(
        tenant_id=tenant_id,
        identifier_type="email",
        identifier_hash="0" * 64,
    )


class TestValueIsEncryptedUnderTheTenantKey:
    async def test_stored_column_is_not_the_plaintext(self):
        identifier = _identifier()

        identifier.set_identifier_value("alice@example.com")

        stored = identifier._identifier_value_encrypted
        assert stored is not None
        assert stored != "alice@example.com"

    async def test_value_round_trips_through_the_property(self):
        identifier = _identifier()

        identifier.set_identifier_value("alice@example.com")

        assert identifier.identifier_value == "alice@example.com"

    async def test_two_tenants_do_not_share_ciphertext(self):
        """The whole point of threading tenant_id through: identical plaintext
        under different tenants must not produce identical ciphertext, or the
        per-tenant key scheme is decorative."""
        first = _identifier(tenant_id=7)
        second = _identifier(tenant_id=8)

        first.set_identifier_value("alice@example.com")
        second.set_identifier_value("alice@example.com")

        assert first._identifier_value_encrypted != second._identifier_value_encrypted
        assert first.identifier_value == second.identifier_value == "alice@example.com"

    async def test_none_stays_none(self):
        identifier = _identifier()

        identifier.set_identifier_value(None)

        assert identifier._identifier_value_encrypted is None
        assert identifier.identifier_value is None


class TestLegacyRowsStillRead:
    async def test_plaintext_written_before_encryption_is_returned_as_is(self):
        """Existing rows are plaintext. They must remain readable rather than
        raising or returning ciphertext-looking garbage to the API."""
        identifier = _identifier()
        identifier._identifier_value_encrypted = "legacy@example.com"

        assert identifier.identifier_value == "legacy@example.com"

    async def test_value_encrypted_under_the_global_key_still_reads(self):
        """decrypt_pii dual-reads (tenant DEK, tenant-salted, true-global), so a
        value written before tenant_id was threaded through still decrypts."""
        identifier = _identifier()
        identifier._identifier_value_encrypted = encrypt_pii("global@example.com")

        assert identifier.identifier_value == "global@example.com"


class TestTheConstructorRefusesTheValue:
    async def test_passing_identifier_value_fails_loudly(self):
        """A kwarg would be encrypted before tenant_id is necessarily set,
        silently falling back to the global key. Fail instead."""
        with pytest.raises(AttributeError):
            CDPProfileIdentifier(
                tenant_id=7,
                identifier_type="email",
                identifier_hash="0" * 64,
                identifier_value="alice@example.com",
            )


class TestColumnWidth:
    async def test_column_holds_the_ciphertext_of_the_longest_input(self):
        column = CDPProfileIdentifier.__table__.c["identifier_value"]
        declared = column.type.length

        ciphertext = encrypt_pii("x" * _MAX_INPUT, 7)

        assert declared is not None
        assert (
            len(ciphertext) <= declared
        ), f"ciphertext is {len(ciphertext)} chars, column holds {declared}"
