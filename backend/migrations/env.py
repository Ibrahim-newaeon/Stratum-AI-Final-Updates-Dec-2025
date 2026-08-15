# =============================================================================
# Stratum AI - Alembic Migration Environment
# =============================================================================
"""
Alembic environment configuration for database migrations.
Uses synchronous migrations for simplicity and reliability.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine, text
from sqlalchemy.engine import Connection

from app.core.config import settings
from app.db.base import Base
from app.models import *  # noqa: F401, F403 - Import all models for metadata

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from settings."""
    return settings.database_url_sync


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        version_num_width=128,
    )

    with context.begin_transaction():
        context.run_migrations()


def _ensure_wide_version_table(connection: Connection) -> None:
    """Make ``alembic_version.version_num`` wide enough for our revision ids.

    Alembic hardcodes that column as ``VARCHAR(32)`` and offers no supported
    way to change it — ``version_num_width`` was passed to ``context.configure``
    here for exactly this reason, but no such option exists. ``configure()``
    takes ``**kw`` and drops unknown keys silently, so it neither worked nor
    complained.

    Several revision ids are longer than 32 characters
    (``041_add_superadmin_to_userrole_enum`` is 35), so ``upgrade head`` against
    a fresh database died partway with::

        StringDataRightTruncation: value too long for type character varying(32)

    and rolled the whole run back, leaving no schema at all. Creating the table
    ourselves first means Alembic finds it already present and leaves it alone.
    The ALTER covers databases stamped before this fix.
    """
    create_sql = (
        "CREATE TABLE IF NOT EXISTS alembic_version ("
        "version_num VARCHAR(255) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )
    widen_sql = (
        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
    )

    connection.execute(text(create_sql))
    connection.execute(text(widen_sql))
    connection.commit()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    _ensure_wide_version_table(connection)

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using sync engine.
    """
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 10},
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
