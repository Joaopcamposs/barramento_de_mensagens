"""Módulo de configuração e gerenciamento do banco de dados."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import registry

from messagebus.entities import UserSecurity

mapper_registry = registry()

engine: AsyncEngine | None = None


def get_database_uri() -> str:
    """
    Monta a URI de conexão com o banco de dados.

    Lê variáveis de ambiente diretamente (sem cache) para garantir
    que testes nunca conectem ao banco de produção.

    Returns:
        URI de conexão formatada.
    """
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
    await session.execute(text(f'SET search_path TO "{schema}"'))
    session.schema = str(schema)


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
    async with get_async_sql_engine().begin() as conn:
        result = await conn.execute(
            text("SELECT schema_name FROM information_schema.schemata")
        )
        return [row[0] for row in result if row[0] not in SCHEMAS_TO_NOT_LIST]


async def delete_schema(schema_id: str) -> None:
    async with get_async_sql_engine().begin() as conn:
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_id}" CASCADE;'))


async def validate_company_email(email: str) -> None:
    """
    Percorre a tabela public.public_user e verifica se o hash do email
    é igual a algum existente.
    """
    email_hash = UserSecurity.hash_email(email)
    async with get_async_sql_engine().begin() as conn:
        result = await conn.execute(
            text(
                f"SELECT email_hash FROM public.public_user WHERE email_hash = '{email_hash}'"
            )
        )
        if result.fetchone():
            raise ValueError(f"Email {email} já existe em outra empresa!")
