"""
Alembic environment configuration.
Reads settings from app/core/config.py and uses the ORM models for autogenerate support.
"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Add backend/ to Python path so app.* imports work ────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Import application settings and all models ────────────────────────────────
from app.core.config import settings
from app.repositories.database import Base

# Import all model modules so their tables are registered on Base.metadata.
# Without this, autogenerate will produce empty migrations.
import app.models.models  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Use the application DATABASE_URL, not the ini file default.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up logging from the ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — no DB connection needed."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — with a real DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
