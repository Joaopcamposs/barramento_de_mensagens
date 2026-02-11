"""Módulo principal da aplicação FastAPI."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from business_contexts.adapters.orm import start_mappers
from business_contexts.entrypoints.api.company import router as company_router
from business_contexts.entrypoints.api.user import router as user_router
from infra.database import get_async_sql_engine, mapper_registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação: cria tabelas e inicializa mappers."""
    engine = get_async_sql_engine()
    async with engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.create_all)

    start_mappers()
    yield


app = FastAPI(
    title="API",
    lifespan=lifespan,
)


@app.get("/")
async def health_check() -> dict[str, str]:
    """Endpoint de health check da API."""
    return {"message": "API is running!"}


app.include_router(company_router)
app.include_router(user_router)
