"""Módulo principal da aplicação FastAPI."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from business_contexts.entrypoints.api.audit_log import router as audit_log_router
from business_contexts.entrypoints.api.company import router as company_router
from business_contexts.entrypoints.api.security import security_router
from business_contexts.entrypoints.api.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Cria a primeira empresa e usuário do sistema, se ainda não existirem."""
    from infra.database.initializers import create_first_company_and_user

    await create_first_company_and_user()
    yield


app = FastAPI(
    title="API Barramento de Mensagens",
    description="APIs REST",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Endpoint de health check da API."""
    return {"message": "API is running!"}


app.include_router(audit_log_router)
app.include_router(company_router)
app.include_router(user_router)
app.include_router(security_router)
