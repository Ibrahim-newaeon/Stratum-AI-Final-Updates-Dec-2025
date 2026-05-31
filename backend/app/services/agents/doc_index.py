# =============================================================================
# Stratum AI - Copilot Doc Index (Phase D foundation)
# =============================================================================
"""
Indexing + retrieval helpers for the Copilot RAG bridge.

Three responsibilities:

1. **Chunk** Stratum markdown docs at paragraph boundaries with a
   target character budget (`copilot_rag_chunk_chars`). Headings are
   carried into chunk metadata so retrieval can show the operator
   *which doc, which section* a citation came from.

2. **Embed** chunks via OpenAI `text-embedding-3-small` (1536-dim) and
   upsert into `copilot_doc_chunks`. Idempotent on re-index — the
   unique constraint on (source_path, chunk_index) means re-running
   the indexer just refreshes existing rows.

3. **Retrieve** the top-K nearest chunks to a query embedding using
   pgvector's cosine-distance ANN index. Returns content + citation
   metadata. Used by `copilot_llm.generate_llm_message` (PR2).

Failure semantics: every public function tolerates a missing
`OPENAI_API_KEY` by raising `RagDisabledError`, which the bridge can
catch and fall back to non-RAG behavior. No user-facing surface
should rely on this without checking `settings.copilot_rag_enabled`
first.

Curated corpus (this PR1):
    docs/00-overview/**/*.md
    docs/04-features/**/*.md
    docs/07-user-guide/**/*.md
    docs/architecture/trust-engine.md
    docs/architecture/system-architecture.md
    docs/00-overview/glossary.md
    docs/03-frontend/figma-theme.md
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Errors
# =============================================================================


class RagDisabledError(RuntimeError):
    """Raised when RAG is requested but the OPENAI_API_KEY is missing."""


# =============================================================================
# Chunking
# =============================================================================


@dataclass(frozen=True)
class DocChunk:
    """A single chunked passage of a markdown doc, ready to embed."""

    source_path: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)


def _walk_headings(text_content: str) -> List[Dict[str, Any]]:
    """Return [(char_offset, level, title), ...] for every markdown heading."""
    return [
        {"offset": m.start(), "level": len(m.group(1)), "title": m.group(2)}
        for m in _HEADING_RE.finditer(text_content)
    ]


def _heading_path_for_offset(
    headings: Sequence[Dict[str, Any]], offset: int
) -> List[str]:
    """Find the active heading hierarchy at a given character offset."""
    stack: List[Dict[str, Any]] = []
    for h in headings:
        if h["offset"] > offset:
            break
        # Pop deeper-or-equal levels — sibling headings replace each other.
        while stack and stack[-1]["level"] >= h["level"]:
            stack.pop()
        stack.append(h)
    return [h["title"] for h in stack]


def chunk_markdown(
    source_path: str,
    text_content: str,
    target_chars: int = 1200,
) -> List[DocChunk]:
    """
    Split a markdown file into chunks at paragraph boundaries.

    A chunk is grown by accumulating paragraphs (separated by blank
    lines) until the next paragraph would push it past `target_chars`.
    Code fences are kept intact — they don't get split mid-block.

    The first chunk includes any frontmatter / preface above the first
    heading. Each chunk's metadata records the active heading path at
    its starting offset so retrieval can show "Trust Engine » Phases".
    """
    if not text_content.strip():
        return []

    headings = _walk_headings(text_content)
    paragraphs = _split_paragraphs(text_content)

    chunks: List[DocChunk] = []
    buf: List[str] = []
    buf_len = 0
    chunk_offset = 0  # char offset of the first paragraph in `buf`
    current_offset = 0  # advances as we consume paragraphs

    def flush() -> None:
        nonlocal buf, buf_len, chunk_offset
        if not buf:
            return
        content = "\n\n".join(buf).strip()
        if not content:
            buf = []
            buf_len = 0
            return
        heading_path = _heading_path_for_offset(headings, chunk_offset)
        title = heading_path[-1] if heading_path else Path(source_path).stem
        chunks.append(
            DocChunk(
                source_path=source_path,
                chunk_index=len(chunks),
                content=content,
                metadata={
                    "title": title,
                    "heading_path": heading_path,
                    "char_offset": chunk_offset,
                    "char_length": len(content),
                },
            )
        )
        buf = []
        buf_len = 0

    for paragraph, paragraph_offset in paragraphs:
        p_len = len(paragraph)
        if buf and buf_len + p_len + 2 > target_chars:
            flush()
            chunk_offset = paragraph_offset
        if not buf:
            chunk_offset = paragraph_offset
        buf.append(paragraph)
        buf_len += p_len + 2
        current_offset = paragraph_offset + p_len

    flush()
    return chunks


def _split_paragraphs(text_content: str) -> List[tuple[str, int]]:
    """
    Yield (paragraph, char_offset) pairs. Code fences (``` blocks) are
    treated as a single indivisible paragraph regardless of internal
    blank lines.
    """
    out: List[tuple[str, int]] = []
    pos = 0
    fence_re = re.compile(r"^```", re.MULTILINE)
    while pos < len(text_content):
        # Detect a code fence at the next non-blank line.
        rest = text_content[pos:]
        leading_ws = re.match(r"\A\s*", rest)
        ws_len = len(leading_ws.group(0)) if leading_ws else 0
        body_pos = pos + ws_len
        if body_pos >= len(text_content):
            break

        if text_content[body_pos : body_pos + 3] == "```":
            # Find the matching closing fence on its own line.
            close = fence_re.search(text_content, body_pos + 3)
            if close is None:
                # Unterminated fence — treat the rest as one paragraph.
                out.append((text_content[body_pos:].rstrip(), body_pos))
                break
            end = close.end()
            # Consume to end-of-line of the closing fence.
            newline = text_content.find("\n", end)
            if newline == -1:
                newline = len(text_content)
            out.append((text_content[body_pos:newline].rstrip(), body_pos))
            pos = newline + 1
            continue

        # Plain paragraph: read until the next blank line.
        next_blank = re.search(r"\n\s*\n", text_content[body_pos:])
        if next_blank is None:
            paragraph = text_content[body_pos:].rstrip()
            if paragraph:
                out.append((paragraph, body_pos))
            break
        paragraph_end = body_pos + next_blank.start()
        paragraph = text_content[body_pos:paragraph_end].rstrip()
        if paragraph:
            out.append((paragraph, body_pos))
        pos = body_pos + next_blank.end()
    return out


# =============================================================================
# Curated corpus
# =============================================================================


CURATED_GLOBS: tuple[str, ...] = (
    "docs/00-overview/**/*.md",
    "docs/04-features/**/*.md",
    "docs/07-user-guide/**/*.md",
    "docs/architecture/trust-engine.md",
    "docs/architecture/system-architecture.md",
    "docs/03-frontend/figma-theme.md",
)


def find_corpus_files(repo_root: Path) -> List[Path]:
    """Resolve every glob in CURATED_GLOBS to its actual files."""
    seen: set[Path] = set()
    result: List[Path] = []
    for pattern in CURATED_GLOBS:
        for match in repo_root.glob(pattern):
            if match.is_file() and match not in seen:
                seen.add(match)
                result.append(match)
    return sorted(result)


# =============================================================================
# Embedding
# =============================================================================


async def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """
    Get OpenAI embeddings for a batch of strings. 1536-dim each.
    Caller is responsible for not passing more than the batch limit
    (OpenAI accepts up to 2048 inputs per call).
    """
    if not settings.openai_api_key:
        raise RagDisabledError("OPENAI_API_KEY is not configured")
    if not texts:
        return []

    # Imported lazily so the package isn't required when RAG is off.
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model=settings.copilot_rag_embedding_model,
        input=list(texts),
    )
    return [row.embedding for row in response.data]


# =============================================================================
# Indexing (write)
# =============================================================================


def _vector_literal(values: Sequence[float]) -> str:
    """Render a Python float list as a pgvector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


async def upsert_chunks(
    db: AsyncSession,
    chunks: Sequence[DocChunk],
    embeddings: Sequence[Sequence[float]],
    *,
    indexed_at_sql: str = "now()",
) -> int:
    """
    Upsert (source_path, chunk_index) → (content, embedding, metadata).
    Returns the number of rows touched.

    Run inside the caller's transaction; the caller commits.
    """
    if not chunks:
        return 0
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks/embeddings length mismatch: {len(chunks)} vs {len(embeddings)}"
        )

    written = 0
    for chunk, embedding in zip(chunks, embeddings):
        await db.execute(
            text(f"""
                INSERT INTO copilot_doc_chunks
                    (source_path, chunk_index, content, embedding, metadata, indexed_at)
                VALUES
                    (:source_path, :chunk_index, :content, :embedding, :metadata, {indexed_at_sql})
                ON CONFLICT (source_path, chunk_index)
                DO UPDATE SET
                    content    = EXCLUDED.content,
                    embedding  = EXCLUDED.embedding,
                    metadata   = EXCLUDED.metadata,
                    indexed_at = EXCLUDED.indexed_at
                """),
            {
                "source_path": chunk.source_path,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "embedding": _vector_literal(embedding),
                "metadata": chunk.metadata,
            },
        )
        written += 1
    return written


async def delete_stale_chunks(
    db: AsyncSession,
    source_path: str,
    keep_max_index: int,
) -> int:
    """
    Drop chunks whose chunk_index >= `keep_max_index` for a given file
    — used after re-indexing a file with fewer chunks than before.
    Returns the number of rows deleted.
    """
    result = await db.execute(
        text("""
            DELETE FROM copilot_doc_chunks
             WHERE source_path = :source_path
               AND chunk_index >= :keep_max_index
            """),
        {"source_path": source_path, "keep_max_index": keep_max_index},
    )
    return result.rowcount or 0


# =============================================================================
# Retrieval (read)
# =============================================================================


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by similarity search, ordered closest-first."""

    source_path: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any]
    distance: float


async def retrieve_top_k(
    db: AsyncSession,
    query: str,
    *,
    top_k: Optional[int] = None,
    min_distance: float = 1.0,
) -> List[RetrievedChunk]:
    """
    Return the `top_k` chunks most similar to `query` by cosine distance.
    `min_distance` (≤1 by definition for cosine) drops trivially-bad matches.
    Returns [] if the OpenAI key isn't configured (RAG silently off).
    """
    if not settings.openai_api_key:
        return []

    k = top_k if top_k is not None else settings.copilot_rag_top_k
    [vector] = await embed_texts([query])

    rows = await db.execute(
        text("""
            SELECT source_path, chunk_index, content, metadata,
                   embedding <=> :vector AS distance
              FROM copilot_doc_chunks
             WHERE embedding <=> :vector < :min_distance
             ORDER BY distance ASC
             LIMIT :k
            """),
        {
            "vector": _vector_literal(vector),
            "min_distance": min_distance,
            "k": k,
        },
    )

    return [
        RetrievedChunk(
            source_path=row.source_path,
            chunk_index=row.chunk_index,
            content=row.content,
            metadata=row.metadata or {},
            distance=float(row.distance),
        )
        for row in rows
    ]


# =============================================================================
# Reindex orchestration (used by app.scripts.index_copilot_docs)
# =============================================================================


async def reindex_file(
    db: AsyncSession,
    source_path: str,
    text_content: str,
    *,
    target_chars: Optional[int] = None,
    embed_batch: int = 64,
) -> int:
    """
    Re-chunk + re-embed + upsert one markdown file. Drops any stale
    chunks beyond the new chunk count. Returns the number of chunks
    written (0 if the file embedded as empty).
    """
    chunks = chunk_markdown(
        source_path=source_path,
        text_content=text_content,
        target_chars=target_chars or settings.copilot_rag_chunk_chars,
    )
    if not chunks:
        await delete_stale_chunks(db, source_path, keep_max_index=0)
        return 0

    embeddings: List[List[float]] = []
    for start in range(0, len(chunks), embed_batch):
        batch = chunks[start : start + embed_batch]
        vectors = await embed_texts([c.content for c in batch])
        embeddings.extend(vectors)

    await upsert_chunks(db, chunks, embeddings)
    await delete_stale_chunks(db, source_path, keep_max_index=len(chunks))
    return len(chunks)


__all__ = [
    "CURATED_GLOBS",
    "DocChunk",
    "RagDisabledError",
    "RetrievedChunk",
    "chunk_markdown",
    "delete_stale_chunks",
    "embed_texts",
    "find_corpus_files",
    "reindex_file",
    "retrieve_top_k",
    "upsert_chunks",
]
