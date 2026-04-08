"""Módulo de configuração e gerenciamento do banco de dados."""

import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import registry

from libs.security import UserSecurity

mapper_registry = registry()

engine: AsyncEngine | None = None

_SAFE_SCHEMA_RE = re.compile(
    r"^(public|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)


def _normalize_database_url(database_url: str) -> str:
    """Normaliza URLs Postgres para o driver asyncpg usado pelo SQLAlchemy."""
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


def validate_schema_name(schema: str) -> str:
    """Valida nomes de schema permitidos antes de interpolar comandos DDL."""
    if not _SAFE_SCHEMA_RE.match(schema):
        raise ValueError(f"Schema invalido: {schema}")
    return schema


def get_database_uri() -> str:
    """
    Monta a URI de conexão com o banco de dados.

    Lê variáveis de ambiente diretamente (sem cache) para garantir
    que testes nunca conectem ao banco de produção.

    Returns:
        URI de conexão formatada.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        database_url = _normalize_database_url(database_url)
        if os.getenv("TEST_ENV", "false").lower() == "true" and database_url.endswith(
            "/postgres"
        ):
            raise RuntimeError(
                "TEST_ENV está ativo mas DATABASE_URL aponta para o banco 'postgres'. "
                "Use um banco de testes dedicado."
            )
        if os.getenv("IN_DOCKER", "false").lower() == "true":
            database_url = database_url.replace(":54322/", ":5432/")
        return database_url

    test_environment = os.getenv("TEST_ENV", "false").lower() == "true"
    in_docker = os.getenv("IN_DOCKER", "false").lower() == "true"

    host = os.getenv("DB_HOST", "localhost")
    password = os.getenv("DB_PASSWORD", "password")
    user = os.getenv("DB_USER", "postgres")
    db_name = os.getenv("DB_NAME", "postgres")

    default_port = 54322
    if any([test_environment, in_docker]):
        default_port = 5432

    port = int(os.getenv("DB_PORT", default_port))

    if test_environment and db_name == "postgres":
        raise RuntimeError(
            "TEST_ENV está ativo mas DB_NAME é 'postgres' (banco de produção). "
            "Defina DB_NAME=test_db para ambiente de testes."
        )

    database_uri = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
    return database_uri


async def set_schema_name(session: AsyncSession, schema: str) -> None:
    """Ajusta o search_path da sessão para o schema informado."""
    safe_schema = validate_schema_name(schema)
    await session.execute(text(f'SET search_path TO "{safe_schema}"'))
    session.schema = safe_schema


def get_async_sql_engine(
    isolation_level: str = "READ COMMITTED",
    force_create_engine: bool = False,
) -> AsyncEngine:
    """
    Retorna ou cria a engine assíncrona do SQLAlchemy.

    Args:
        isolation_level: Nível de isolamento da transação.
        force_create_engine: Se True, cria uma nova engine sem pool.

    Returns:
        Engine assíncrona do SQLAlchemy.
    """

    def _create_engine() -> AsyncEngine:
        """Cria uma nova engine ou reutiliza a engine global configurada."""
        global engine

        if force_create_engine:
            return create_async_engine(
                get_database_uri(),
                isolation_level=isolation_level,
                future=True,
                poolclass=NullPool,
            )

        if not engine:
            engine = create_async_engine(
                get_database_uri(),
                isolation_level=isolation_level,
                future=True,
                pool_pre_ping=True,
            )
        return engine

    return _create_engine()


async def default_async_sql_session_factory(
    read_only: bool,
    schema: str | None = None,
    isolation_level: str = "READ COMMITTED",
    force_create_engine: bool = False,
) -> AsyncSession:
    """
    Cria uma sessão SQLAlchemy assíncrona.

    Deve ser utilizada internamente em estruturas que lidam com contextos,
    como o Unit of Work.

    Args:
        read_only: Se True, cria sessão somente leitura com AUTOCOMMIT.
        schema: Schema a ser utilizado na sessão.
        isolation_level: Nível de isolamento da transação.
        force_create_engine: Se True, força criação de nova engine.

    Returns:
        Sessão assíncrona do SQLAlchemy.
    """
    _engine = get_async_sql_engine(
        isolation_level=isolation_level, force_create_engine=force_create_engine
    )

    schema_in_use = schema or "public"
    execution_options = dict(schema_translate_map={None: schema_in_use})

    if read_only:
        execution_options["isolation_level"] = "AUTOCOMMIT"

    session = AsyncSession(
        bind=_engine.execution_options(**execution_options),
        autoflush=True,
        expire_on_commit=False,
    )
    await set_schema_name(session, schema_in_use)

    async def async_close() -> None:
        """Fecha a sessão assíncrona criada pela factory."""
        await session.close()

    session.async_close = async_close  # type: ignore[attr-defined]

    return session


@asynccontextmanager
async def get_session(
    read_only: bool, schema: str = "public"
) -> AsyncGenerator[AsyncSession, None]:
    """
    Gerenciador de contexto para criar e fechar sessões automaticamente.

    Deve ser usada em contextos abertos diretamente, sem uso do Unit of Work.

    Args:
        read_only: Se True, cria sessão somente leitura.
        schema: Schema a ser utilizado

    Yields:
        Sessão assíncrona do SQLAlchemy.
    """
    session = await default_async_sql_session_factory(read_only=read_only, schema=schema)
    try:
        yield session
    finally:
        await session.close()


SCHEMAS_TO_NOT_LIST: tuple[str, ...] = (
    "public",
    "information_schema",
    "pg_catalog",
    "pg_toast",
)


async def list_existing_schemas() -> list[str]:
    """Lista os schemas de tenant existentes no banco."""
    async with get_async_sql_engine().begin() as conn:
        result = await conn.execute(
            text("SELECT schema_name FROM information_schema.schemata")
        )
        return [row[0] for row in result if row[0] not in SCHEMAS_TO_NOT_LIST]


async def delete_schema(schema_id: str) -> None:
    """Remove um schema de tenant e seus objetos, se ele existir."""
    safe_schema = validate_schema_name(schema_id)
    async with get_async_sql_engine().begin() as conn:
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{safe_schema}" CASCADE;'))


async def validate_company_email(email: str) -> None:
    """
    Percorre a tabela public.public_user e verifica se o hash do email
    é igual a algum existente.
    """
    email_hash = UserSecurity.compute_email_lookup_hmac(email)
    async with get_async_sql_engine().begin() as conn:
        public_user_exists = await conn.execute(
            text("SELECT to_regclass('public.public_user')")
        )
        if not public_user_exists.fetchone():
            return

        result = await conn.execute(
            text(
                "SELECT 1 FROM public.public_user WHERE email_lookup_hmac = :email_lookup_hmac"
            ),
            {"email_lookup_hmac": email_hash},
        )
        if result.fetchone():
            raise ValueError(f"Email {email} já existe em outra empresa!")
