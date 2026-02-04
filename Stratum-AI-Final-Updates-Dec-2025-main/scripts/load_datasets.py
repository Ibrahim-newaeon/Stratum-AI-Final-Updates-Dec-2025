"""
Stratum AI - Platform Datasets Loader

Loads synthetic ad datasets into PostgreSQL for development and testing.
Dynamically creates tables based on CSV structure.
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://stratum:stratum_secure_password_2024@localhost:5432/stratum_ai",
)

# Datasets base path
DATASETS_PATH = Path(__file__).parent.parent / "datasets"


def create_warehouse_schema(engine):
    """Create warehouse schema."""
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS warehouse CASCADE"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS warehouse"))
        conn.commit()
    print("✅ Warehouse schema created")


def infer_sql_type(dtype, col_name):
    """Infer SQL type from pandas dtype."""
    dtype_str = str(dtype)
    col_lower = col_name.lower()

    # Check column name patterns first
    if "date" in col_lower:
        return "DATE"
    if col_lower in ["id", "tenant_id"]:
        return "INTEGER"
    if "_id" in col_lower:
        return "VARCHAR(100)"
    if "name" in col_lower or "type" in col_lower:
        return "VARCHAR(500)"

    # Check dtype
    if "int" in dtype_str:
        return "BIGINT"
    elif "float" in dtype_str:
        return "DECIMAL(15,4)"
    elif "bool" in dtype_str:
        return "BOOLEAN"
    elif "datetime" in dtype_str:
        return "TIMESTAMP"
    else:
        return "TEXT"


def create_table_from_df(engine, df, table_name, schema="warehouse"):
    """Create table based on DataFrame structure."""
    columns = []
    for col in df.columns:
        sql_type = infer_sql_type(df[col].dtype, col)
        columns.append(f'"{col}" {sql_type}')

    # Add ID and created_at
    column_defs = ",\n        ".join(columns)

    ddl = f"""
    DROP TABLE IF EXISTS {schema}.{table_name} CASCADE;
    CREATE TABLE {schema}.{table_name} (
        id BIGSERIAL PRIMARY KEY,
        {column_defs},
        created_at TIMESTAMP DEFAULT NOW()
    )
    """

    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()


def load_csv_to_table(engine, csv_path: Path, table_name: str, schema: str = "warehouse"):
    """Load a CSV file into a database table with dynamic schema."""

    if not csv_path.exists():
        print(f"⚠️  File not found: {csv_path}")
        return 0

    print(f"📂 Loading {csv_path.name}...")

    try:
        df = pd.read_csv(csv_path, low_memory=False)

        # Clean column names (remove spaces, lowercase)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        # Add tenant_id if not present
        if "tenant_id" not in df.columns:
            df["tenant_id"] = 1

        # Handle date columns
        date_cols = [c for c in df.columns if "date" in c.lower()]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors="coerce")

        # Create table dynamically
        create_table_from_df(engine, df, table_name, schema)

        # Load data in chunks
        row_count = len(df)
        chunk_size = 5000

        for i in range(0, row_count, chunk_size):
            chunk = df.iloc[i : i + chunk_size]
            chunk.to_sql(
                table_name, engine, schema=schema, if_exists="append", index=False, method="multi"
            )
            if row_count > chunk_size:
                print(
                    f"   ... loaded {min(i+chunk_size, row_count):,}/{row_count:,} rows", end="\r"
                )

        print(f"   ✅ Loaded {row_count:,} rows into {schema}.{table_name}      ")
        return row_count

    except Exception as e:
        print(f"   ❌ Error loading {csv_path.name}: {e}")
        return 0


def create_indexes(engine):
    """Create performance indexes on fact tables."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_fact_daily_date ON warehouse.fact_daily(date)",
        "CREATE INDEX IF NOT EXISTS idx_fact_daily_platform ON warehouse.fact_daily(platform)",
        "CREATE INDEX IF NOT EXISTS idx_fact_daily_campaign ON warehouse.fact_daily(campaign_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_daily_tenant ON warehouse.fact_daily(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_daily_geo ON warehouse.fact_daily(geo)",
    ]

    with engine.connect() as conn:
        for idx in indexes:
            try:
                conn.execute(text(idx))
            except Exception:
                pass  # Index might already exist or column missing
        conn.commit()

    print("✅ Indexes created")


def main():
    """Main entry point for data loading."""

    print("=" * 70)
    print("🚀 Stratum AI - Platform Datasets Loader")
    print("=" * 70)
    print()

    # Connect to database
    print("📡 Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("   ✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        sys.exit(1)

    print()

    # Create warehouse schema
    print("📋 Creating warehouse schema...")
    create_warehouse_schema(engine)
    print()

    # Find available datasets
    if not DATASETS_PATH.exists():
        print(f"❌ Datasets folder not found: {DATASETS_PATH}")
        sys.exit(1)

    dataset_dirs = [d for d in DATASETS_PATH.iterdir() if d.is_dir()]
    print(f"📁 Found {len(dataset_dirs)} dataset(s): {', '.join(d.name for d in dataset_dirs)}")
    print()

    # Track loaded tables to avoid duplicates
    loaded_tables = set()
    total_rows = 0

    # Load each dataset
    for dataset_dir in dataset_dirs:
        print("-" * 70)
        print(f"📦 Processing dataset: {dataset_dir.name}")
        print("-" * 70)

        # Get all CSV files
        csv_files = list(dataset_dir.glob("*.csv"))

        for csv_file in csv_files:
            # Determine table name from filename
            base_name = csv_file.stem.lower()

            # Skip data dictionary
            if "dictionary" in base_name:
                continue

            # For regional fact tables, consolidate into fact_daily
            if base_name.startswith("fact_daily"):
                table_name = "fact_daily"
            else:
                table_name = base_name

            # Load the file
            rows = load_csv_to_table(engine, csv_file, table_name)
            total_rows += rows
            loaded_tables.add(table_name)

        print()

    # Create indexes
    print("📊 Creating indexes...")
    create_indexes(engine)
    print()

    # Summary
    print("=" * 70)
    print("✅ Data Loading Complete!")
    print("=" * 70)
    print(f"   📈 Total rows loaded: {total_rows:,}")
    print(f"   📋 Tables created: {len(loaded_tables)}")
    print()

    # Verify counts
    print("📋 Table row counts:")
    with engine.connect() as conn:
        for table in sorted(loaded_tables):
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM warehouse.{table}"))
                count = result.scalar()
                print(f"   warehouse.{table}: {count:,} rows")
            except Exception as e:
                print(f"   warehouse.{table}: Error - {e}")

    print()
    print("🎉 Done! Your data is ready in the warehouse schema.")


if __name__ == "__main__":
    main()
