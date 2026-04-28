---
name: db-query-review
description: Use when reviewing or writing new SQL/SQLAlchemy queries, especially in `backend/app/services/`, `backend/app/models/`, or migration files. Catches missing tenant filters, N+1 queries, async-session misuse, and missing indexes before they reach production. Trigger when the user says "review this query", "check for N+1", "is this query safe", or modifies repo-layer code.
---

# Database Query Review

SQLAlchemy 2.x async on PostgreSQL is fast and powerful — and easy to misuse. The bugs surface at scale, not in tests. This skill is the pre-merge checklist.

## The Checklist

For every new or changed query, verify ALL of:

### 1. Tenant filter present

Any query against a tenant-scoped table (anything with a `tenant_id` column) MUST include `WHERE tenant_id = :tenant_id`.

```python
# ❌ Bad
await db.execute(select(Event).where(Event.id == event_id))
# ✅ Good
await db.execute(select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id))
```

Defer deep checks to the `tenancy-auditor` agent.

### 2. Async session pattern correct

```python
# ❌ Bad — sync session in async function
def get_user(db: Session, id: int): ...

# ❌ Bad — session held across network call
async with async_session() as db:
    user = await db.get(User, id)
    result = await external_api.fetch(user.email)  # session still open!
    user.last_synced = result.at
    await db.commit()

# ✅ Good — close session before network, open new one for write
async with async_session() as db:
    user = await db.get(User, id)
result = await external_api.fetch(user.email)
async with async_session() as db:
    user = await db.get(User, id)
    user.last_synced = result.at
    await db.commit()
```

### 3. No N+1 queries

```python
# ❌ Bad
segments = (await db.scalars(select(Segment))).all()
for s in segments:
    members = (await db.scalars(select(Member).where(Member.segment_id == s.id))).all()

# ✅ Good — eager load
stmt = select(Segment).options(selectinload(Segment.members))
segments = (await db.scalars(stmt)).all()
```

Watch for: `for x in result: query(x.related)`. Use `selectinload`, `joinedload`, or a single JOIN.

### 4. Index supports the WHERE / ORDER BY

- WHERE on a non-indexed column at scale = sequential scan = production fire.
- Confirm there is an index on every column used in `WHERE`, `JOIN`, `ORDER BY`.
- Composite indexes for multi-column filters: index `(tenant_id, status, created_at)` not three separate indexes.

Check existing indexes:

```bash
grep -rn "Index\|index=True\|__table_args__" backend/app/models/<file>.py
```

### 5. LIMIT on potentially-large result sets

Anything that could return >1000 rows must have `.limit(...)` or pagination.

- List endpoints: always paginate (`limit`, `offset` or cursor).
- Bulk reads in tasks: stream with `.execution_options(stream_results=True)` or batch via `LIMIT/OFFSET`.

### 6. No SELECT \*

Use explicit columns or load only needed relationships. Reduces wire size and lock contention.

### 7. UPDATE/DELETE has WHERE

```python
# ❌ Catastrophic
await db.execute(delete(User))
# ✅ Good
await db.execute(delete(User).where(User.id == user_id, User.tenant_id == tenant_id))
```

Sounds obvious. Has happened.

### 8. Bulk operations use bulk APIs

Looping `db.add(...)` then `commit()` for 10,000 rows = slow and may exceed connection timeout. Use `db.execute(insert(Model).values([...]))` or `bulk_insert_mappings`.

### 9. EXPLAIN ANALYZE before merge (for new hot-path queries)

```bash
# Inside psql connected to dev DB
EXPLAIN (ANALYZE, BUFFERS) <your-query>;
```

- Look for `Seq Scan` on large tables → missing index.
- `Buffers: shared read=N` where N is large → not in cache, will be slow on cold start.
- `Rows Removed by Filter` >> `Rows` → query is over-fetching then filtering in memory.

### 10. Migrations safe (delegate)

If the change adds an index or alters a table, run the `migration-auditor` agent before merging.

## Quick scan commands

```bash
# Find all queries in the diff
git diff main...HEAD -- backend/app/ | grep -E '^\+' | grep -iE 'select\(|\.scalars\(|\.execute\(|insert\(|update\(|delete\('

# Find loops with queries inside (N+1 candidates)
git diff main...HEAD -- backend/app/ | grep -B 2 -A 5 -E '^\+[[:space:]]*for ' | grep -E 'await.*execute|await.*scalars'

# Find sessions held across awaits (async-session misuse)
grep -rn "async with .*session" backend/app/ | head
```

## Red flags worth a second look

| Pattern                                       | Why it's risky                                        |
| --------------------------------------------- | ----------------------------------------------------- |
| `for x in items: await db.execute(...)`       | Almost always N+1                                     |
| `.all()` without `.limit()`                   | Unbounded result set                                  |
| `func.lower(col) == ...` in WHERE             | Index can't be used unless there's a functional index |
| `OR` across two columns with separate indexes | Postgres often can't use either                       |
| `created_at::date = ...`                      | Same — kills index usage on `created_at`              |
| `LIKE '%foo%'`                                | Sequential scan unless you have a trigram index       |
| Subquery in SELECT clause                     | Often an N+1 in disguise                              |

## When to escalate

- Query touches a table with >1M rows and you're not sure about lock impact → `migration-auditor`.
- Query crosses tenants intentionally (admin/aggregation) → `tenancy-auditor` to confirm safe.
- Adding an index → `migration-auditor` (must be `CONCURRENTLY`).
