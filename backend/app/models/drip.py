# =============================================================================
# Stratum AI - Drip Campaign Models
# =============================================================================
"""SQLAlchemy models for drip (email sequence) campaigns.

Persists drip sequences and their execution logs so that data survives
process restarts and is shared across API workers — replacing the former
per-process in-memory store, which lost data on restart and was invisible
across workers.

Sequences keep their flow graph (nodes + edges + trigger config) as JSONB.
Identifiers retain the legacy ``drip_<hex>`` / ``exec_<hex>`` string format
so the API contract and any persisted frontend references are unchanged.
"""

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


def generate_sequence_id() -> str:
    """Generate a drip-sequence identifier (legacy ``drip_<hex>`` format)."""
    return f"drip_{secrets.token_hex(8)}"


def generate_execution_id() -> str:
    """Generate a drip-execution identifier (legacy ``exec_<hex>`` format)."""
    return f"exec_{secrets.token_hex(8)}"


def generate_version_id() -> str:
    """Generate a drip sequence-version identifier (``dripv_<hex>``)."""
    return f"dripv_{secrets.token_hex(8)}"


def generate_enrollment_id() -> str:
    """Generate a drip-enrollment identifier (``enroll_<hex>``)."""
    return f"enroll_{secrets.token_hex(8)}"


# ---------------------------------------------------------------------------
# Enrollment state machine
# ---------------------------------------------------------------------------
# PENDING    enrolled, no step executed yet; the sweep will pick it up
# ACTIVE     a worker holds the claim and is executing a step right now
# WAITING    parked on a wait node until next_due_at
# COMPLETED  reached an end node
# CANCELLED  unsubscribed, sequence archived, or stopped by hand
# FAILED     a step exhausted its retries
#
# FAILED is not in the original five. Without it an enrollment whose step keeps
# raising has nowhere to land: it either stays WAITING and is retried forever,
# or is marked COMPLETED and reports a sequence that finished when it did not.
ENROLLMENT_PENDING = "pending"
ENROLLMENT_ACTIVE = "active"
ENROLLMENT_WAITING = "waiting"
ENROLLMENT_COMPLETED = "completed"
ENROLLMENT_CANCELLED = "cancelled"
ENROLLMENT_FAILED = "failed"

#: Statuses that mean "this recipient is still moving through the sequence".
#: The partial unique index below is scoped to exactly this set, so a recipient
#: can be re-enrolled after finishing but never enrolled twice at once.
ENROLLMENT_IN_FLIGHT = (
    ENROLLMENT_PENDING,
    ENROLLMENT_ACTIVE,
    ENROLLMENT_WAITING,
)

#: Hard ceiling on node transitions for a single enrollment. The flow builder
#: lets a user draw an edge back to an earlier node, so a condition that always
#: takes the same branch is a live infinite loop. Reaching this marks the
#: enrollment FAILED rather than letting a worker spin.
MAX_ENROLLMENT_STEPS = 100


class DripSequence(Base):
    """A drip (email) sequence defined by a drag-and-drop flow graph."""

    __tablename__ = "drip_sequences"

    id = Column(String(64), primary_key=True, default=generate_sequence_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="", server_default="")
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status = Column(String(20), nullable=False, default="draft", server_default="draft")

    # Flow graph
    nodes = Column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    edges = Column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )

    # Aggregate counters
    entry_count = Column(Integer, nullable=False, default=0, server_default="0")
    active_recipient_count = Column(
        Integer, nullable=False, default=0, server_default="0"
    )
    completion_rate = Column(Float, nullable=False, default=0.0, server_default="0")
    revenue_attributed_cents = Column(
        BigInteger, nullable=False, default=0, server_default="0"
    )

    # The published graph currently being entered. `nodes`/`edges` above stay
    # the editable draft; activating freezes a copy into a DripSequenceVersion
    # and points this at it. Enrollments reference the version, never the draft,
    # so editing a live sequence cannot strand an in-flight recipient on a node
    # that no longer exists.
    active_version_id = Column(
        String(64),
        ForeignKey("drip_sequence_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    active_version = relationship(
        "DripSequenceVersion", foreign_keys=[active_version_id], post_update=True
    )

    __table_args__ = (Index("ix_drip_sequence_tenant_status", "tenant_id", "status"),)


class DripExecutionRecord(Base):
    """A single send/open/click event for a drip sequence recipient."""

    __tablename__ = "drip_execution_logs"

    id = Column(String(64), primary_key=True, default=generate_execution_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id = Column(
        String(64),
        ForeignKey("drip_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The enrollment this event belongs to. Nullable for rows written before
    # the execution engine existed, when the endpoint recorded standalone
    # "simulated" sends with nothing to attach them to.
    enrollment_id = Column(
        String(64),
        ForeignKey("drip_enrollments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Encrypted under this row's tenant key, matching DripEnrollment. This
    # column held plaintext addresses while nothing wrote to it; the execution
    # engine writes real recipients, so it cannot stay in the clear.
    _recipient_email_encrypted = Column("recipient_email", String(1024), nullable=False)
    #: Deterministic hash, for looking an event up without decrypting.
    recipient_hash = Column(String(64), nullable=True, index=True)

    def set_recipient_email(self, value: str) -> None:
        """Encrypt the address under this row's tenant key and set the hash.

        A method rather than a settable property, for the same reason as
        :meth:`DripEnrollment.set_recipient_email` — see the note there.
        """
        from app.core.security import encrypt_pii, hash_pii_for_lookup

        normalised = value.strip().lower()
        self._recipient_email_encrypted = encrypt_pii(normalised, self.tenant_id)
        self.recipient_hash = hash_pii_for_lookup(normalised)

    @property
    def recipient_email(self) -> Optional[str]:
        """The decrypted address."""
        stored = self._recipient_email_encrypted
        if stored is None:
            return None

        from app.core.security import decrypt_pii

        try:
            return decrypt_pii(stored, self.tenant_id)
        except ValueError:
            return stored

    step_number = Column(Integer, nullable=False, default=0, server_default="0")
    node_type = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    extra = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_drip_exec_sequence", "sequence_id", "sent_at"),
        Index("ix_drip_exec_enrollment", "enrollment_id", "sent_at"),
    )


class DripSequenceVersion(Base):
    """An immutable snapshot of a sequence's flow graph at publish time.

    A sequence's ``nodes``/``edges`` are an editable draft. Every activation
    freezes them here and bumps ``version``. Enrollments point at the version
    they entered on, so a marketer editing a running sequence changes what new
    recipients get without rewriting the path the current ones are walking.

    The trigger is frozen alongside the graph: changing ``trigger_config`` is a
    change to who enters and on what, which is as much a new sequence as moving
    an edge.
    """

    __tablename__ = "drip_sequence_versions"

    id = Column(String(64), primary_key=True, default=generate_version_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id = Column(
        String(64),
        ForeignKey("drip_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: 1-based, monotonic per sequence.
    version = Column(Integer, nullable=False)

    # Frozen copies. Deliberately duplicated rather than referenced.
    nodes = Column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    edges = Column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    #: The node the interpreter starts from — resolved and stored at publish
    #: time so the worker never has to re-scan the graph for the trigger node.
    entry_node_id = Column(String(64), nullable=False)

    published_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    published_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("sequence_id", "version", name="uq_drip_version_sequence"),
        Index("ix_drip_version_tenant", "tenant_id", "sequence_id"),
    )


class DripEnrollment(Base):
    """Where one recipient currently stands inside one sequence run.

    ``drip_execution_logs`` records what already happened; this records what
    happens next. Without it a sequence cannot be resumed after a restart,
    cannot be paused mid-flight, and cannot tell whether a recipient is already
    walking it — every one of which the sweep task needs on each tick.

    The sweep claims rows with ``status IN (pending, waiting)`` and
    ``next_due_at <= now()``, so those two columns carry the hot index.
    """

    __tablename__ = "drip_enrollments"

    id = Column(String(64), primary_key=True, default=generate_enrollment_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id = Column(
        String(64),
        ForeignKey("drip_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id = Column(
        String(64),
        ForeignKey("drip_sequence_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # -- recipient ---------------------------------------------------------
    # The CDP profile, when the trigger knows it. Nullable because a
    # user_subscribed trigger can fire on an address that has no profile yet,
    # and SET NULL rather than CASCADE because deleting a profile must not
    # silently delete the record that we mailed that person.
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cdp_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    #: Deterministic SHA256 of the normalised address (``hash_pii_for_lookup``).
    #: Every lookup, dedupe and uniqueness check goes through this column —
    #: ``encrypt_pii`` is non-deterministic, so the ciphertext below cannot be
    #: compared or indexed.
    recipient_hash = Column(String(64), nullable=False, index=True)

    # Encrypted under this row's tenant key, following CDPProfileIdentifier /
    # AudienceSyncCredential rather than app.db.types.EncryptedString: a
    # TypeDecorator is handed the bare value and never the row, so it cannot
    # reach tenant_id and would put every tenant under one global-derived key.
    #
    # Width holds ciphertext, not input: RFC 5321 caps an address at 320 and
    # encrypt_pii is ~2.2x, so 320 would reject the longest legitimate address.
    _recipient_email_encrypted = Column("recipient_email", String(1024), nullable=False)

    # -- position ----------------------------------------------------------
    status = Column(
        String(20), nullable=False, default=ENROLLMENT_PENDING, server_default="pending"
    )
    #: Node in the pinned version's graph that this enrollment is sitting on.
    #: NULL only while PENDING, before the first step runs.
    current_node_id = Column(String(64), nullable=True)
    #: When the sweep should next consider this row. NULL for terminal states.
    next_due_at = Column(DateTime(timezone=True), nullable=True)
    #: Transitions made so far, checked against MAX_ENROLLMENT_STEPS.
    steps_completed = Column(Integer, nullable=False, default=0, server_default="0")

    # -- worker claim ------------------------------------------------------
    # Kept separate from `status` so a crashed worker's claim expires on its own
    # rather than leaving the row stuck in ACTIVE with nothing holding it.
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    claimed_by = Column(String(64), nullable=True)

    # -- provenance and failure -------------------------------------------
    entry_trigger = Column(String(50), nullable=False)
    #: What the trigger saw — event id, cart id, campaign id. Kept for
    #: personalisation and for explaining afterwards why someone was enrolled.
    entry_context = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)
    cancel_reason = Column(String(100), nullable=True)

    # -- timestamps --------------------------------------------------------
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    sequence = relationship("DripSequence", foreign_keys=[sequence_id])
    version = relationship("DripSequenceVersion", foreign_keys=[version_id])

    # -- PII accessors -----------------------------------------------------
    def set_recipient_email(self, value: str) -> None:
        """Encrypt the address under this row's tenant key and set the hash.

        A method, not a settable property: SQLAlchemy's declarative constructor
        applies kwargs in the order given, so a property could encrypt before
        ``tenant_id`` was assigned and fall back to the global key while looking
        entirely successful. Set ``tenant_id`` first, then call this.
        """
        from app.core.security import encrypt_pii, hash_pii_for_lookup

        normalised = value.strip().lower()
        self._recipient_email_encrypted = encrypt_pii(normalised, self.tenant_id)
        self.recipient_hash = hash_pii_for_lookup(normalised)

    @property
    def recipient_email(self) -> Optional[str]:
        """The decrypted address, for sending and for display."""
        stored = self._recipient_email_encrypted
        if stored is None:
            return None

        from app.core.security import decrypt_pii

        try:
            return decrypt_pii(stored, self.tenant_id)
        except ValueError:
            # Matches CDPProfileIdentifier: a row written before encryption is
            # returned as-is rather than breaking the whole listing.
            return stored

    __table_args__ = (
        # One live enrollment per recipient per sequence. Partial, so finishing
        # a sequence frees the recipient to be enrolled again later — which a
        # plain unique constraint would forbid forever.
        Index(
            "uq_drip_enrollment_live",
            "sequence_id",
            "recipient_hash",
            unique=True,
            postgresql_where=text("status IN ('pending', 'active', 'waiting')"),
        ),
        # The sweep's only query: due work, oldest first.
        Index(
            "ix_drip_enrollment_due",
            "status",
            "next_due_at",
            postgresql_where=text("status IN ('pending', 'waiting')"),
        ),
        Index("ix_drip_enrollment_tenant_status", "tenant_id", "status"),
        Index("ix_drip_enrollment_sequence_status", "sequence_id", "status"),
    )
