import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import tvbf.app.models  # noqa: F401
import tvbf.catalog.models  # noqa: F401
from tvbf.config import get_settings
from tvbf.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in ("app", "catalog")
    return True


# The search indexes only the migrations create, by design: the folded ones are expression
# indexes over `immutable_unaccent` that the models can't declare (see `catalog.models.Person`),
# and the two raw-column ones were never declared either, so the test suite's `create_all`
# needs no pg_trgm. Autogenerate would otherwise read each as a removed index, and CI's
# `alembic check` (NEU-2235) would fail on them. Listed by name, not by an `_trgm` suffix, so
# a new migration-only index has to be added here on purpose.
MIGRATION_ONLY_INDEXES = frozenset(
    {
        "ix_person_name_folded_trgm",
        "ix_show_name_folded_trgm",
        "ix_show_name_trgm",
        "ix_show_aka_title_folded_trgm",
        "ix_show_aka_title_trgm",
    }
)


def include_object(object_, name, type_, reflected, compare_to):
    return not (
        type_ == "index" and reflected and compare_to is None and name in MIGRATION_ONLY_INDEXES
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        version_table_schema="app",
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        version_table_schema="app",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
