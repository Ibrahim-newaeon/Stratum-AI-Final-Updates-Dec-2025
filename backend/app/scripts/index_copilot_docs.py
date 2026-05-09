# =============================================================================
# Stratum AI - Copilot Doc Indexer (CLI)
# =============================================================================
"""
Re-index the curated Stratum docs corpus into `copilot_doc_chunks`.

Usage:
    python -m app.scripts.index_copilot_docs                # all curated docs
    python -m app.scripts.index_copilot_docs path/to/file.md ...  # specific files
    python -m app.scripts.index_copilot_docs --dry-run      # chunk + count, no embed/write

Run from the `backend/` directory after `make migrate` so the
`copilot_doc_chunks` table exists. Requires `OPENAI_API_KEY` in the
env unless `--dry-run` is set.

Idempotent on re-run; the unique constraint on (source_path,
chunk_index) means re-running just refreshes existing rows.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services.agents.doc_index import (
    CURATED_GLOBS,
    RagDisabledError,
    chunk_markdown,
    find_corpus_files,
    reindex_file,
)

logger = get_logger(__name__)


# Repo root, two levels up from this file (backend/app/scripts/this.py -> backend/.. -> repo)
REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_targets(args: List[str]) -> List[Path]:
    """Either explicit paths or the curated corpus."""
    if args:
        out: List[Path] = []
        for arg in args:
            p = Path(arg)
            if not p.is_absolute():
                p = REPO_ROOT / p
            if p.is_file() and p.suffix == ".md":
                out.append(p)
            elif p.is_dir():
                out.extend(sorted(p.rglob("*.md")))
            else:
                logger.warning("indexer_skipping_invalid_path", path=str(p))
        return out
    return find_corpus_files(REPO_ROOT)


async def _run_dry(files: List[Path]) -> None:
    total_chunks = 0
    for path in files:
        text_content = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(
            source_path=str(path.relative_to(REPO_ROOT)),
            text_content=text_content,
            target_chars=settings.copilot_rag_chunk_chars,
        )
        total_chunks += len(chunks)
        print(f"  {path.relative_to(REPO_ROOT)}  →  {len(chunks)} chunks")
    print(f"\nTotal: {len(files)} files, {total_chunks} chunks (no embeddings written).")


async def _run_index(files: List[Path]) -> None:
    if not settings.openai_api_key:
        raise RagDisabledError(
            "OPENAI_API_KEY is not set — set it in the environment or use --dry-run"
        )

    written = 0
    async with async_session_factory() as session:
        async with session.begin():
            for path in files:
                rel = str(path.relative_to(REPO_ROOT))
                text_content = path.read_text(encoding="utf-8")
                count = await reindex_file(session, rel, text_content)
                print(f"  {rel}  →  {count} chunks")
                written += count
    print(f"\nIndexed {written} chunks across {len(files)} files.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-index Stratum docs for the Copilot RAG bridge."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific .md files or directories to index. Defaults to the curated corpus.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chunk and report sizes without calling OpenAI or writing to the database.",
    )
    parsed = parser.parse_args()

    files = _resolve_targets(parsed.paths)
    if not files:
        if parsed.paths:
            print("No matching .md files found.", file=sys.stderr)
        else:
            print(
                "Curated corpus matched zero files. Verify globs in doc_index.CURATED_GLOBS:\n  "
                + "\n  ".join(CURATED_GLOBS),
                file=sys.stderr,
            )
        return 1

    print(f"Target: {len(files)} markdown file(s).")
    if parsed.dry_run:
        asyncio.run(_run_dry(files))
        return 0
    try:
        asyncio.run(_run_index(files))
    except RagDisabledError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
