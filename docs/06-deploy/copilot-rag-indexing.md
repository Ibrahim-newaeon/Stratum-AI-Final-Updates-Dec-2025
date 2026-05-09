# Activation Checklist — Copilot RAG (Phases D-1 + D-2)

The Copilot RAG bridge is shipped in three pieces. This doc covers
**Phase D Part 1 — indexing infrastructure** and **Phase D Part 2 —
bridge wiring + citations**. The bridge is now active; toggling
`COPILOT_RAG_ENABLED=true` will retrieve docs and pass them to Claude.

**Phase D Part 3** (SSE streaming) is a separate PR.

## What this PR ships

```
backend/migrations/versions/049_copilot_doc_chunks.py     pgvector + table
backend/app/models/copilot_doc.py                         CopilotDocChunk model
backend/app/services/agents/doc_index.py                  chunking + embed + retrieve
backend/app/scripts/index_copilot_docs.py                 CLI re-indexer
backend/requirements.txt                                  openai==1.54.0, pgvector==0.3.6
backend/app/core/config.py                                copilot_rag_* settings
```

The bridge calls `retrieve_top_k()` only when `COPILOT_RAG_ENABLED=true`.
Until PR 2 lands, that flag has no consumer — toggling it on does
nothing except make the indexer require an OpenAI key.

## Step 1 — Run the migration

```
make migrate
```

Adds the `vector` extension and the `copilot_doc_chunks` table. If
your Postgres image doesn't include pgvector (vanilla `postgres:16`
does _not_), pull `pgvector/pgvector:pg16` first. The migration is
no-op on re-run.

## Step 2 — Get an OpenAI API key

1. https://platform.openai.com → API keys → Create
2. Treat like Stripe — store in your password manager, never paste
   in chat.
3. Set a usage cap (Settings → Limits) — `text-embedding-3-small`
   is `$0.02 / 1M tokens`. Re-indexing the curated corpus once costs
   well under a penny.

## Step 3 — Set Railway env vars

| Variable                      | Value                         |
| ----------------------------- | ----------------------------- |
| `OPENAI_API_KEY`              | the `sk-…` key from Step 2    |
| `COPILOT_RAG_ENABLED`         | `true` once PR2 is merged + corpus indexed |
| `COPILOT_RAG_EMBEDDING_MODEL` | `text-embedding-3-small`      |
| `COPILOT_RAG_TOP_K`           | `4` (default)                 |
| `COPILOT_RAG_CHUNK_CHARS`     | `1200` (default)              |

## Step 4 — Index the curated corpus

From inside the backend container or Railway shell:

```
python -m app.scripts.index_copilot_docs
```

Output looks like:

```
Target: 32 markdown file(s).
  docs/00-overview/glossary.md  →  9 chunks
  docs/00-overview/vision.md  →  4 chunks
  ...
Indexed 187 chunks across 32 files.
```

The CLI is idempotent — re-running just refreshes existing rows. Run
it after every meaningful docs edit; you can hook it into CI later.

To verify before committing OpenAI spend:

```
python -m app.scripts.index_copilot_docs --dry-run
```

## Step 5 — Verify in Postgres

```
SELECT count(*) FROM copilot_doc_chunks;
SELECT source_path, count(*) FROM copilot_doc_chunks GROUP BY source_path ORDER BY 2 DESC LIMIT 10;
```

Expected: ~150–200 chunks across ~30 files for the curated corpus.

## Step 6 — Smoke a retrieval (manual)

The bridge isn't wired yet, but you can test retrieval directly:

```python
import asyncio
from app.db.session import async_session_factory
from app.services.agents.doc_index import retrieve_top_k

async def main():
    async with async_session_factory() as db:
        chunks = await retrieve_top_k(db, "What is signal health?", top_k=3)
        for c in chunks:
            print(f"{c.source_path}#{c.chunk_index}  d={c.distance:.3f}")
            print(c.content[:200], "...\n")

asyncio.run(main())
```

Expected: top hit is the trust-engine or glossary doc.

## Rollback

The migration's `downgrade()` drops the table and indexes. The
extension is left in place for future tables.

```
alembic downgrade 048
```

## Cost monitoring

Re-indexing the curated corpus is a one-shot cost (~$0.001). Once
PR 2 wires retrieval, every Copilot question costs 1 embedding call
(~$0.00002) before the Claude completion — negligible. Track via
the structlog event `copilot_rag_retrieved` (added in PR 2).

## Adjusting the corpus

Edit `CURATED_GLOBS` in `backend/app/services/agents/doc_index.py`.
Re-run the indexer. Stale chunks for files that no longer match are
automatically dropped per-file by `reindex_file()`'s
`delete_stale_chunks()`, but files removed from the glob list aren't
auto-cleaned — drop them manually:

```
DELETE FROM copilot_doc_chunks WHERE source_path = 'docs/old-thing.md';
```

## Out of scope (deferred)

- Streaming responses + frontend EventSource — PR 3.
- Auto-reindex on docs/ edits — would need a CI job or git hook.
- Per-tenant docs (e.g. tenant-uploaded help articles) — current
  scope is platform docs only.

## Owner

Same as Phase D Part 0 (the original LLM bridge): operator setting
the env vars must have **superadmin** role on the platform. The
OpenAI key is workspace-scoped to your OpenAI account, not bound
to a Stratum user.
