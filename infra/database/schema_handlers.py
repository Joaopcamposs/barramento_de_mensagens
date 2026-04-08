"""Módulo de manipulação de schemas do banco de dados multi-tenant."""

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from infra.database import get_async_sql_engine, validate_schema_name
from infra.database.migrations import create_schema_and_run_migrations


async def verify_existing_schema(conn: AsyncConnection, schema_id: str) -> None:
    """Verifica se o schema já existe no banco de dados."""
    safe_schema = validate_schema_name(schema_id)
    result = await conn.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_id"
        ),
        {"schema_id": safe_schema},
    )
    if result.fetchone():
        raise ValueError(f"Schema {safe_schema} já existe")


async def create_schema_and_tables(schema_id: str) -> None:
    """
    Cria o schema e suas tabelas no banco de dados via Alembic.
    """
    safe_schema = validate_schema_name(schema_id)
    engine_temp = get_async_sql_engine(force_create_engine=True)
    try:
        async with engine_temp.begin() as conn:
            await verify_existing_schema(conn, safe_schema)
        await create_schema_and_run_migrations(safe_schema)
    finally:
        await engine_temp.dispose()


async def create_full_schema_within_transaction(
    session_factory: Callable,
    schema_id: str | None,
) -> AsyncSession:
    """Cria o schema completo e retorna uma sessão vinculada a ele."""
    if schema_id is None:
        raise ValueError("schema_id é obrigatório para criar schema completo")

    safe_schema = validate_schema_name(str(schema_id))
    await create_schema_and_tables(schema_id=safe_schema)
    session = await session_factory(
        read_only=False, schema=safe_schema, force_create_engine=True
    )

    return session
