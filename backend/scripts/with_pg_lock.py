#!/usr/bin/env python
"""Run a command while holding a Postgres session-level advisory lock [INF-011].

Serializes the database bootstrap (migrations + DDL + seeds in ``release.sh``)
across concurrent API replicas. The first replica to reach it acquires the lock
and runs the command; the others block until it is released, then run the same
(idempotent) command as a no-op. Without this, every replica ran
``alembic upgrade head`` simultaneously on boot, racing the ``alembic_version``
row and the ``CREATE CAST`` / ``UPDATE`` statements in ``release.sh``.

Usage::

    python scripts/with_pg_lock.py <command> [args...]

If ``DATABASE_URL_SYNC`` is unset the command is run directly, without a lock,
so local tooling that has no database configured still works.
"""

import os
import subprocess
import sys

# Stable arbitrary positive 64-bit key namespacing this lock to the Stratum DB
# bootstrap. Must be identical across every replica for them to contend.
_LOCK_KEY = 0x53545241_54554D01  # "STRA" "TUM\x01" — fits signed bigint

# Cap how long a replica waits for the lock before failing out (letting the
# platform restart policy retry). Comfortably longer than release.sh's 120s
# alembic timeout so the holder always finishes first under normal conditions.
_LOCK_TIMEOUT_MS = 300_000


def _run(argv: list[str]) -> int:
    return subprocess.call(argv)


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print("with_pg_lock: no command given", file=sys.stderr)
        return 2

    sync_url = os.environ.get("DATABASE_URL_SYNC")
    if not sync_url:
        print("with_pg_lock: DATABASE_URL_SYNC unset; running without lock")
        return _run(argv)

    import sqlalchemy
    from sqlalchemy import text

    engine = sqlalchemy.create_engine(sync_url)
    # AUTOCOMMIT keeps no transaction open; the session-level advisory lock is
    # still held on this connection until pg_advisory_unlock or session end.
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        conn.execute(text(f"SET lock_timeout = {_LOCK_TIMEOUT_MS}"))
        print(f"with_pg_lock: acquiring advisory lock {_LOCK_KEY}...", flush=True)
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _LOCK_KEY})
        print("with_pg_lock: lock acquired", flush=True)
        try:
            return _run(argv)
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _LOCK_KEY})
            print("with_pg_lock: lock released", flush=True)
    finally:
        conn.close()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
