# =============================================================================
# Stratum AI — Migration: copilot doc chunks (Phase D foundation)
# =============================================================================
"""
Foundation for the Copilot RAG bridge. Enables the pgvector extension
and creates the `copilot_doc_chunks` table that holds chunked Stratum
documentation with OpenAI text-embedding-3-small embeddings (1536-dim).

Population is out-of-band via `python -m app.scripts.index_copilot_docs`
— this migration ships only the schema. The bridge stays off until
PR 2 wires retrieval into copilot_llm.

Schema:
  id           BIGSERIAL PRIMARY KEY
  source_path  TEXT NOT NULL          ← e.g. "docs/04-features/cdp.md"
  chunk_index  INTEGER NOT NULL       ← 0-based position within the file
  content      TEXT NOT NULL          ← the chunk text we send to Claude
  embedding    vector(1536) NOT NULL  ← OpenAI text-embedding-3-small
  metadata     JSONB NOT NULL DEFAULT '{}'  ← title, heading path, char span
  indexed_at   TIMESTAMPTZ NOT NULL DEFAULT now()

Indexes:
  - (source_path, chunk_index) UNIQUE — re-index is upsert-safe
  - vector index using HNSW with cosine distance — sub-10ms top-k=4
    on ~1k chunks
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = "049_copilot_doc_chunks"
down_revision = "048_autopilot_outcome_columns"
branch_labels = None
depends_on = None


def _extension_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = :name"),
        {"name": name},
    )
    return result.first() is not None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :table"),
        {"table": table},
    )
    return result.first() is not None


def upgrade() -> None:
    # 1. pgvector. Idempotent on re-run; "IF NOT EXISTS" so we don't choke
    #    on environments where the operator pre-installed it.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if _table_exists("copilot_doc_chunks"):
        return

    # 2. Table. Use raw DDL because SQLAlchemy core doesn't have a
    #    first-class vector type without the pgvector dialect plugin,
    #    and we want this migration to run cleanly even when the Python
    #    pgvector package isn't installed (e.g. CI without RAG enabled).
    op.execute("""
        CREATE TABLE copilot_doc_chunks (
            id           BIGSERIAL PRIMARY KEY,
            source_path  TEXT NOT NULL,
            chunk_index  INTEGER NOT NULL,
            content      TEXT NOT NULL,
            embedding    vector(1536) NOT NULL,
            metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
            indexed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """)

    # 3. Lookup indexes. Unique on (source_path, chunk_index) lets the
    #    indexer upsert per chunk without duplicates.
    op.execute(
        "CREATE UNIQUE INDEX copilot_doc_chunks_source_chunk_uq "
        "ON copilot_doc_chunks (source_path, chunk_index)"
    )

    # 4. Vector ANN index. HNSW with cosine distance is fastest for our
    #    expected scale (~1k chunks). m=16, ef_construction=64 are the
    #    pgvector defaults; tune later if recall is poor.
    op.execute(
        "CREATE INDEX copilot_doc_chunks_embedding_hnsw "
        "ON copilot_doc_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS copilot_doc_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS copilot_doc_chunks_source_chunk_uq")
    op.execute("DROP TABLE IF EXISTS copilot_doc_chunks")
    # Don't drop the extension — other tables may use it later. Leaving
    # the extension in place is the safe default for an additive
    # downgrade.
