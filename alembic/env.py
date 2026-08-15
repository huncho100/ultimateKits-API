from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from app.core.config import settings
from app.database.database import Base

# Import all models here so Alembic can detect them
from app.models.user import User


# ============================================================
# Alembic Config
# ============================================================

config = context.config


# ============================================================
# Set database URL from application settings
# ============================================================

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL,
)


# ============================================================
# Configure Python logging
# ============================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# SQLAlchemy metadata
# ============================================================

target_metadata = Base.metadata


# ============================================================
# Offline migrations
# ============================================================

def run_migrations_offline() -> None:
    """
    Run migrations in offline mode.

    This generates SQL without requiring a live database connection.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# Online migrations
# ============================================================

def run_migrations_online() -> None:
    """
    Run migrations in online mode.

    This connects directly to PostgreSQL.
    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================
# Run migration
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()