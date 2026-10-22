import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import db

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Each role keeps its tables in its own schema, the version table lives in public
SCHEMAS = ("bff", "agent")


def _url() -> str:
    url = config.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return db.async_url(url)


def _only_bff(name, type_, parent_names) -> bool:
    # Autogenerate compares only our schema, tables of other roles are theirs
    return type_ != "schema" or name == db.SCHEMA


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=db.metadata,
        include_schemas=True,
        include_name=_only_bff,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as connection:
        for schema in SCHEMAS:
            await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        await connection.commit()
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline SQL generation is not supported, run against a database")
asyncio.run(_run_async())
