"""Módulo principal da aplicação FastAPI."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from business_contexts.entrypoints.api.company import router as company_router
from business_contexts.entrypoints.api.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Cria a primeira empresa e usuário do sistema, se ainda não existirem."""
    from infra.database.initializers import create_first_company_and_user

    await create_first_company_and_user()
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
