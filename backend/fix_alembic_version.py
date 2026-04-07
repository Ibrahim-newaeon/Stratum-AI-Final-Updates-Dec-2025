"""Fix alembic_version column width before running migrations."""
import os
import psycopg2

url = os.environ.get("DATABASE_URL_SYNC", "")
if not url:
    print("DATABASE_URL_SYNC not set, skipping")
    exit(0)

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(128) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )
    cur.execute(
        "ALTER TABLE alembic_version "
        "ALTER COLUMN version_num TYPE VARCHAR(128)"
    )
    conn.commit()
    cur.close()
    conn.close()
    print("alembic_version column widened to VARCHAR(128)")
except Exception as e:
    print(f"alembic fix skipped: {e}")
