# =============================================================================
# Stratum AI - Copilot Doc Chunk Model
# =============================================================================
"""
SQLAlchemy model for `copilot_doc_chunks` — chunked Stratum docs with
OpenAI text-embedding-3-small embeddings used by the RAG bridge.

Foundation only: this model declares the columns; retrieval lives in
`app.services.agents.doc_index`. The bridge stays off until the
COPILOT_RAG_ENABLED feature flag flips.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class CopilotDocChunk(Base):
    """One chunk of indexed Stratum documentation."""

    __tablename__ = "copilot_doc_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # The vector column is created via raw DDL in migration 049 because
    # SQLAlchemy core doesn't have a first-class pgvector type without the
    # pgvector-python dialect plugin. We touch the column from Python only
    # via raw SQL in `app.services.agents.doc_index`, so an ORM mapping
    # isn't required — but we declare it as Text so SELECT * round-trips
    # don't error. Don't write to it via ORM; use the raw SQL helpers.
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index(
            "copilot_doc_chunks_source_chunk_uq",
            "source_path",
            "chunk_index",
            unique=True,
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover — debugging only
        return (
            f"<CopilotDocChunk id={self.id} source={self.source_path!r} "
            f"chunk={self.chunk_index}>"
        )
