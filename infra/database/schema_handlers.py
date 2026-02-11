"""Módulo de manipulação de schemas do banco de dados multi-tenant."""

from collections.abc import Callable

from sqlalchemy import Sequence, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from infra.database import get_async_sql_engine, mapper_registry


async def verify_existing_schema(conn: AsyncConnection, schema_id: str) -> None:
    """Verifica se o schema já existe no banco de dados."""
    result = await conn.execute(
        text(
            f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{schema_id}'"
        )
    )
    if result.fetchone():
        raise ValueError(f"Schema {schema_id} já existe")


async def create_schema_and_tables(schema_id: str) -> None:
    """
    Cria o schema e suas tabelas no banco de dados.

    1. Cria o schema no Postgres
    2. Ajusta os metadados para usar schema_id
    3. Cria as tabelas do tenant dentro dele
    4. Restaura schema=None nos metadados
    """
    engine_temp: AsyncEngine = get_async_sql_engine(force_create_engine=True)

    try:
        async with engine_temp.begin() as conn:
            await verify_existing_schema(conn, schema_id)
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_id}"'))

        for table in mapper_registry.metadata.sorted_tables:
            if table.schema == "public":
                continue
            table.schema = schema_id
            for column in table.columns:
                if isinstance(column.default, Sequence):
                    column.default.schema = schema_id

        async with engine_temp.begin() as conn:
            await conn.run_sync(mapper_registry.metadata.create_all)

        for table in mapper_registry.metadata.sorted_tables:
            if table.schema == schema_id:
                table.schema = None
    finally:
        await engine_temp.dispose()


async def create_full_schema_within_transaction(
    session_factory: Callable,
    schema_id: str | None,
) -> AsyncSession:
    """Cria o schema completo e retorna uma sessão vinculada a ele."""
    await create_schema_and_tables(schema_id=schema_id)

    if schema_id:
        schema_id = str(schema_id)

    session = await session_factory(
        read_only=False, schema=schema_id, force_create_engine=True
    )

    return session
