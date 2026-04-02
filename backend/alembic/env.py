"""
alembic/env.py
--------------
WHAT IS ALEMBIC?
  Alembic is version control for your database schema.

  Instead of manually running ALTER TABLE commands every time you change
  a model, you:
    1. Change your Python model
    2. Run: alembic revision --autogenerate -m "describe the change"
       Alembic compares your models to the real DB and writes a migration script
    3. Run: alembic upgrade head
       This applies the script to the database

  "head" = the latest migration
  "downgrade -1" = revert the most recent migration

WHY ASYNC?
  Our SQLAlchemy engine is async. Standard Alembic is sync.
  run_async_migrations() bridges the gap by running Alembic
  inside asyncio so it can use our async engine.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import ALL models here so Alembic can detect them when autogenerating
from app.models.wallet import Wallet           # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.core.database import Base
from app.core.config import settings

config = context.config

# Override the sqlalchemy.url in alembic.ini with our settings value
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata tells Alembic what the schema SHOULD look like
# It compares this against the real DB to generate migration scripts
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without connecting to the DB (for review)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
