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

import infra.database as db_module
from infra.database import get_async_sql_engine, mapper_registry


@pytest_asyncio.fixture(autouse=True)
async def engine() -> AsyncEngine:
    """Cria a engine de teste e as tabelas do banco a cada teste."""
    import business_contexts.adapters.orm  # noqa: F401 - registra os mappers

    db_module.engine = None

    _engine = get_async_sql_engine(force_create_engine=True)
    async with _engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        for table in reversed(mapper_registry.metadata.sorted_tables):
            await conn.execute(table.delete())
    await _engine.dispose()
