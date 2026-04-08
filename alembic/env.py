"""Ambiente Alembic para executar migracoes nos schemas gerenciados."""

from __future__ import annotations

from logging.config import fileConfig
from uuid import UUID

from alembic.operations.base import Operations
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from infra.database import get_database_uri, validate_schema_name

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_schema = context.get_x_argument(as_dictionary=True).get(
    "schema"
) or config.attributes.get("target_schema")
if target_schema is not None:
    target_schema = validate_schema_name(str(target_schema))


def _is_valid_schema(schema_name: str) -> bool:
    """Retorna ``True`` para `public` e schemas tenant UUID."""
    if schema_name == "public":
        return True
    try:
        UUID(schema_name)
    except ValueError:
        return False
    return True


def _list_target_schemas(connection: Connection) -> list[str]:
    """Lista os schemas alvo da execucao atual."""
    if target_schema is not None:
        return [target_schema]

    rows = connection.execute(
        text(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN (
                'information_schema',
                'pg_catalog',
                'pg_toast'
            )
            ORDER BY schema_name
            """
        )
    )
    return [row[0] for row in rows if _is_valid_schema(row[0])]


def _operation_matches_schema(operation, schema_name: str) -> bool:  # type: ignore[no-untyped-def]
    """Permite rodar apenas operacoes destinadas ao schema atual."""
    operation_schema = getattr(operation, "schema", None)
    if operation_schema is None:
        operation_schema = getattr(operation, "kw", {}).get("source_schema")
    if operation_schema is None:
        return True
    return validate_schema_name(str(operation_schema)) == schema_name


def _run_for_schema(connection: Connection, schema_name: str) -> None:
    """Configura o contexto e executa a migration para um schema."""
    safe_schema = validate_schema_name(schema_name)
    print(f"Running Alembic for schema: {safe_schema}")
    connection.execute(text(f'SET search_path TO "{safe_schema}"'))
    context.configure(
        connection=connection,
        version_table_schema=safe_schema,
        transaction_per_migration=False,
    )

    original_invoke = Operations.invoke

    def _invoke(self, operation):  # type: ignore[no-untyped-def]
        if not _operation_matches_schema(operation, safe_schema):
            return None
        return original_invoke(self, operation)

    Operations.invoke = _invoke
    try:
        context.run_migrations(schema=safe_schema)
    finally:
        Operations.invoke = original_invoke


def run_migrations_offline() -> None:
    """Executa migracoes offline apenas para um schema explicito."""
    if target_schema is None:
        raise RuntimeError("Offline mode requires an explicit target schema.")

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=target_schema,
    )

    with context.begin_transaction():
        context.run_migrations(schema=target_schema)


def run_migrations_online(connection: Connection) -> None:
    """Executa migracoes para todos os schemas gerenciados."""
    for schema_name in _list_target_schemas(connection):
        _run_for_schema(connection, schema_name)


def run_with_connection() -> None:
    """Executa migrations usando conexao injetada ou nova conexao."""
    provided_connection = config.attributes.get("connection")
    if provided_connection is not None:
        run_migrations_online(provided_connection)
        return

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_uri()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def _run_async() -> None:
        import asyncio

        async def _inner() -> None:
            async with connectable.begin() as connection:
                await connection.run_sync(run_migrations_online)
            await connectable.dispose()

        asyncio.run(_inner())

    _run_async()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_with_connection()
