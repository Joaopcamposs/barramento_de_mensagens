"""Helpers para executar migracoes Alembic em schemas explicitos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import create_async_engine

from infra.database import get_database_uri, validate_schema_name


def build_alembic_config(target_schema: str) -> Config:
    """Constroi a configuracao do Alembic com a URL de banco atual."""
    safe_target_schema = validate_schema_name(target_schema)
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", get_database_uri())
    config.attributes["target_schema"] = safe_target_schema
    return config


def _run_schema_command(
    connection: Any,
    action: str,
    target_schema: str,
    revision: str,
) -> None:
    """Executa o comando Alembic usando a conexao/transacao ja aberta."""
    safe_target_schema = validate_schema_name(target_schema)
    config = build_alembic_config(safe_target_schema)
    config.attributes["connection"] = connection

    if action == "upgrade":
        command.upgrade(config, revision)
        return
    if action == "downgrade":
        command.downgrade(config, revision)
        return
    raise ValueError(f"Acao de migracao invalida: {action}")


async def run_migration_for_schemas(
    action: str,
    schemas: list[str],
    revision: str,
) -> None:
    """Executa migracao de forma atomica para todos os schemas informados."""
    if not schemas:
        return

    engine = create_async_engine(get_database_uri(), poolclass=NullPool, future=True)

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                for schema in schemas:
                    safe_schema = validate_schema_name(schema)
                    await connection.execute(
                        text(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}"')
                    )
                    await connection.run_sync(
                        _run_schema_command, action, safe_schema, revision
                    )
            except Exception:
                await transaction.rollback()
                raise
            else:
                await transaction.commit()
    finally:
        await engine.dispose()


async def create_schema_and_run_migrations(
    schema_id: str,
    revision: str = "head",
) -> None:
    """Cria um schema tenant vazio e executa as migracoes Alembic nele."""
    safe_schema = validate_schema_name(schema_id)
    engine = create_async_engine(get_database_uri(), poolclass=NullPool, future=True)

    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}"'))

        await run_migration_for_schemas("upgrade", ["public", safe_schema], revision)
    finally:
        await engine.dispose()
