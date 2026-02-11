"""Configuração de fixtures para testes de integração."""

import os

os.environ["TEST_ENV"] = "true"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "54323"
os.environ["DB_PASSWORD"] = "password"
os.environ["DB_USER"] = "postgres"
os.environ["DB_NAME"] = "test_db"

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from infra.database import get_async_sql_engine, mapper_registry


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncEngine:
    """Cria a engine de teste e as tabelas do banco."""
    import business_contexts.adapters.orm  # noqa: F401 - registra os mappers

    _engine = get_async_sql_engine(force_create_engine=True)
    async with _engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(engine: AsyncEngine) -> None:
    """Limpa todas as tabelas antes de cada teste."""
    async with engine.begin() as conn:
        for table in reversed(mapper_registry.metadata.sorted_tables):
            await conn.execute(table.delete())
