from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import re
from typing import Awaitable, Callable, cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from business_contexts.entrypoints.api.audit_log import router as audit_log_router
from business_contexts.entrypoints.api.company import router as company_router
from business_contexts.entrypoints.api.security import security_router
from business_contexts.entrypoints.api.user import router as user_router
from libs.consts import IS_PROD, SENTRY_DSN
from libs.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Cria a primeira empresa e usuário do sistema, se ainda não existirem."""
    from infra.database.initializers import create_first_company_and_user

    await create_first_company_and_user()
    yield


def get_cors_origins() -> list[str]:
    """Retorna as origens permitidas para CORS a partir do ambiente."""
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if cors_origins:
        return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    if IS_PROD:
        return []
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]


def get_app_version() -> str:
    """Retorna a versão da aplicação a partir do pacote ou pyproject."""
    try:
        return version("barramento-de-mensagens")
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if pyproject.exists():
            match = re.search(
                r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE
            )
            if match:
                return match.group(1)
        return "0.0.0"


if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.0)


app = FastAPI(
    title="API Barramento de Mensagens",
    description="APIs REST",
    version=get_app_version(),
    docs_url=None if IS_PROD else "/api/docs",
    redoc_url=None if IS_PROD else "/api/redoc",
    openapi_url=None if IS_PROD else "/api/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Adapta o handler do SlowAPI para a assinatura esperada pelo Starlette."""
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-turnstile-token"],
)


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Adiciona headers de segurança às respostas HTTP."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
    return response


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Endpoint de health check da API."""
    return {"message": "API is running!"}


app.include_router(audit_log_router)
app.include_router(company_router)
app.include_router(user_router)
app.include_router(security_router)
