"""Testes unitários do contexto de infraestrutura de banco e inicialização."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
import uuid7
from sqlalchemy import Sequence

from infra import database
from infra.database import initializers, schema_handlers
from tests.unit.helpers import FakeAsyncSession, FakeConnection, FakeEngine, FakeResult


class TestDatabaseModule:
    """Testes para funções utilitárias de acesso ao banco."""

    def test_get_database_uri_uses_default_local_port(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Usa porta local padrão quando não está em teste nem docker."""
        monkeypatch.delenv("TEST_ENV", raising=False)
        monkeypatch.delenv("IN_DOCKER", raising=False)
        monkeypatch.setenv("DB_NAME", "tenant_db")
        monkeypatch.setenv("DB_USER", "postgres")
        monkeypatch.setenv("DB_PASSWORD", "secret")
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.delenv("DB_PORT", raising=False)

        uri = database.get_database_uri()

        assert uri == "postgresql+asyncpg://postgres:secret@localhost:54322/tenant_db"

    def test_get_database_uri_uses_test_port_in_test_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Define porta de teste quando TEST_ENV está ativo."""
        monkeypatch.setenv("TEST_ENV", "true")
        monkeypatch.setenv("DB_NAME", "test_db")
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("DB_HOST", "h")
        monkeypatch.delenv("DB_PORT", raising=False)

        uri = database.get_database_uri()

        assert uri.endswith("@h:5432/test_db")

    def test_get_database_uri_blocks_postgres_db_in_test_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bloqueia execução de testes apontando para banco padrão de produção."""
        monkeypatch.setenv("TEST_ENV", "true")
        monkeypatch.setenv("DB_NAME", "postgres")

        with pytest.raises(RuntimeError):
            database.get_database_uri()

    @pytest.mark.asyncio
    async def test_set_schema_name_executes_search_path(self) -> None:
        """Aplica search_path na sessão e persiste schema escolhido."""
        session = FakeAsyncSession()

        await database.set_schema_name(session, "tenant_schema")

        assert session.schema == "tenant_schema"
        assert session.execute_calls

    def test_get_async_sql_engine_caches_singleton(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Garante reutilização da engine global quando não forçada."""
        created: list[str] = []

        def fake_create(*args: Any, **kwargs: Any) -> str:
            created.append("engine")
            return f"engine-{len(created)}"

        monkeypatch.setattr(database, "create_async_engine", fake_create)
        monkeypatch.setattr(database, "engine", None)

        engine_a = database.get_async_sql_engine()
        engine_b = database.get_async_sql_engine()

        assert engine_a == "engine-1"
        assert engine_b == "engine-1"
        assert len(created) == 1

    def test_get_async_sql_engine_force_create_ignores_cache(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cria nova engine quando force_create_engine é verdadeiro."""
        calls: list[dict[str, Any]] = []

        def fake_create(*args: Any, **kwargs: Any) -> str:
            calls.append(kwargs)
            return f"forced-{len(calls)}"

        monkeypatch.setattr(database, "create_async_engine", fake_create)
        monkeypatch.setattr(database, "engine", "cached")

        forced = database.get_async_sql_engine(force_create_engine=True)

        assert forced == "forced-1"
        assert calls[0]["poolclass"].__name__ == "NullPool"
        assert database.engine == "cached"

    @pytest.mark.asyncio
    async def test_default_async_sql_session_factory_sets_autocommit_when_read_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configura sessão read-only com isolation level AUTOCOMMIT."""
        fake_engine = FakeEngine()
        captured: dict[str, Any] = {}

        class SessionCtor(FakeAsyncSession):
            def __init__(self, bind: Any, autoflush: bool, expire_on_commit: bool):
                super().__init__()
                captured["bind"] = bind
                captured["autoflush"] = autoflush
                captured["expire_on_commit"] = expire_on_commit

        monkeypatch.setattr(database, "get_async_sql_engine", lambda **_: fake_engine)
        monkeypatch.setattr(database, "AsyncSession", SessionCtor)

        session = await database.default_async_sql_session_factory(
            read_only=True,
            schema="tenant-r",
        )

        assert isinstance(session, SessionCtor)
        assert fake_engine.execution_options_calls[0]["schema_translate_map"] == {
            None: "tenant-r"
        }
        assert fake_engine.execution_options_calls[0]["isolation_level"] == "AUTOCOMMIT"
        assert captured["autoflush"] is True
        assert captured["expire_on_commit"] is False

        await session.async_close()  # type: ignore[attr-defined]
        assert session.closed is True

    @pytest.mark.asyncio
    async def test_get_session_closes_session_in_context_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fecha sessão automaticamente ao sair do context manager."""
        session = FakeAsyncSession()

        async def fake_factory(**_: Any) -> FakeAsyncSession:
            return session

        monkeypatch.setattr(database, "default_async_sql_session_factory", fake_factory)

        async with database.get_session(read_only=False, schema="public") as yielded:
            assert yielded is session

        assert session.closed is True

    @pytest.mark.asyncio
    async def test_list_existing_schemas_filters_system_schemas(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Retorna somente schemas de tenant, excluindo schemas de sistema."""
        rows = [("public",), ("tenant_1",), ("pg_catalog",), ("tenant_2",)]
        connection = FakeConnection(execute_results=[FakeResult(scalars=rows)])
        engine = FakeEngine(connection=connection)

        monkeypatch.setattr(database, "get_async_sql_engine", lambda: engine)

        schemas = await database.list_existing_schemas()

        assert schemas == ["tenant_1", "tenant_2"]

    @pytest.mark.asyncio
    async def test_delete_schema_executes_drop_statement(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Executa comando de DROP SCHEMA para o tenant informado."""
        connection = FakeConnection()
        engine = FakeEngine(connection=connection)
        monkeypatch.setattr(database, "get_async_sql_engine", lambda: engine)

        await database.delete_schema("tenant-z")

        query_text = str(connection.execute_calls[0])
        assert 'DROP SCHEMA IF EXISTS "tenant-z"' in query_text

    @pytest.mark.asyncio
    async def test_validate_company_email_raises_on_existing_hash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dispara erro quando hash de email já existe no schema público."""
        connection = FakeConnection(execute_results=[FakeResult(fetchone=("hash",))])
        engine = FakeEngine(connection=connection)

        monkeypatch.setattr(database, "get_async_sql_engine", lambda: engine)
        monkeypatch.setattr(
            database.UserSecurity, "hash_email", staticmethod(lambda _: "hash")
        )

        with pytest.raises(ValueError):
            await database.validate_company_email("user@example.com")

    @pytest.mark.asyncio
    async def test_validate_company_email_passes_when_hash_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Não lança erro quando hash de email não existe."""
        connection = FakeConnection(execute_results=[FakeResult(fetchone=None)])
        engine = FakeEngine(connection=connection)

        monkeypatch.setattr(database, "get_async_sql_engine", lambda: engine)
        monkeypatch.setattr(
            database.UserSecurity, "hash_email", staticmethod(lambda _: "hash")
        )

        await database.validate_company_email("new@example.com")


class TestInitializersModule:
    """Testes para inicialização da primeira empresa e usuário."""

    def test_generate_fake_user_for_first_registration(self) -> None:
        """Cria usuário base fake com dados padrão de bootstrap."""
        company_id = uuid7.create()

        user = initializers.generate_fake_user_for_first_registration(company_id)

        assert user.company == company_id
        assert user.cpf == initializers.FIRST_USER_CPF
        assert user.email == initializers.FIRST_USER_EMAIL

    @pytest.mark.asyncio
    async def test_create_first_company_and_user_returns_when_schema_uuid_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Interrompe bootstrap quando já existe schema de tenant válido."""
        existing_uuid = str(uuid7.create())
        called = {"bootstrap": False}

        async def fake_list_existing_schemas() -> list[str]:
            return [existing_uuid]

        monkeypatch.setattr(
            initializers, "list_existing_schemas", fake_list_existing_schemas
        )
        monkeypatch.setattr(
            initializers, "bootstrap", lambda **_: called.__setitem__("bootstrap", True)
        )

        await initializers.create_first_company_and_user()

        assert called["bootstrap"] is False

    @pytest.mark.asyncio
    async def test_create_first_company_and_user_executes_bootstrap_flow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Executa fluxo de criação da primeira empresa e chama mapeadores."""
        company_id = str(uuid7.create())
        bus_calls: list[Any] = []
        start_mappers_called = {"value": False}

        class FakeBus:
            async def handle(self, command: Any) -> None:
                bus_calls.append(command)

        async def fake_list_existing_schemas() -> list[str]:
            return ["invalid-schema"]

        monkeypatch.setattr(initializers, "FIRST_COMPANY_ID", company_id)
        monkeypatch.setattr(
            initializers, "list_existing_schemas", fake_list_existing_schemas
        )
        monkeypatch.setattr(initializers, "bootstrap", lambda **_: FakeBus())
        monkeypatch.setattr(
            initializers,
            "start_mappers",
            lambda: start_mappers_called.__setitem__("value", True),
        )

        await initializers.create_first_company_and_user()

        assert len(bus_calls) == 1
        assert bus_calls[0].legal_name == "JP ADM"
        assert start_mappers_called["value"] is True

    @pytest.mark.asyncio
    async def test_create_first_company_and_user_deletes_schema_on_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Remove schema recém-criado quando bootstrap falha."""
        company_id = str(uuid7.create())
        deleted: list[str] = []

        class FakeBus:
            async def handle(self, command: Any) -> None:
                raise RuntimeError("failure")

        async def fake_list_existing_schemas() -> list[str]:
            return ["not-uuid"]

        async def fake_delete_schema(schema: str) -> None:
            deleted.append(schema)

        monkeypatch.setattr(initializers, "FIRST_COMPANY_ID", company_id)
        monkeypatch.setattr(
            initializers, "list_existing_schemas", fake_list_existing_schemas
        )
        monkeypatch.setattr(initializers, "bootstrap", lambda **_: FakeBus())
        monkeypatch.setattr(initializers, "delete_schema", fake_delete_schema)

        with pytest.raises(RuntimeError, match="failure"):
            await initializers.create_first_company_and_user()

        assert deleted == [company_id]


class TestSchemaHandlers:
    """Testes para criação e validação de schemas multi-tenant."""

    @pytest.mark.asyncio
    async def test_verify_existing_schema_raises_when_schema_exists(self) -> None:
        """Falha ao tentar criar schema já existente."""
        connection = FakeConnection(execute_results=[FakeResult(fetchone=("tenant",))])

        with pytest.raises(ValueError):
            await schema_handlers.verify_existing_schema(connection, "tenant")

    @pytest.mark.asyncio
    async def test_verify_existing_schema_passes_when_schema_not_exists(self) -> None:
        """Permite criação quando schema ainda não existe."""
        connection = FakeConnection(execute_results=[FakeResult(fetchone=None)])

        await schema_handlers.verify_existing_schema(connection, "tenant")

    @pytest.mark.asyncio
    async def test_create_schema_and_tables_updates_and_restores_table_schema(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cria schema de tenant, ajusta metadata e restaura estado original."""
        connection = FakeConnection(execute_results=[FakeResult(fetchone=None)])
        engine = FakeEngine(connection=connection)

        class FakeColumn:
            def __init__(self, default: Any = None) -> None:
                self.default = default

        class FakeTable:
            def __init__(self, schema: str | None, columns: list[FakeColumn]) -> None:
                self.schema = schema
                self.columns = columns

        seq = Sequence("tenant_seq")
        tenant_table = FakeTable(None, [FakeColumn(seq), FakeColumn()])
        public_table = FakeTable("public", [FakeColumn()])
        metadata = SimpleNamespace(
            sorted_tables=[tenant_table, public_table],
            create_all=lambda *_args, **_kwargs: None,
        )

        monkeypatch.setattr(schema_handlers, "get_async_sql_engine", lambda **_: engine)
        monkeypatch.setattr(
            schema_handlers, "mapper_registry", SimpleNamespace(metadata=metadata)
        )

        await schema_handlers.create_schema_and_tables("tenant_new")

        assert tenant_table.schema is None
        assert public_table.schema == "public"
        assert seq.schema == "tenant_new"
        assert engine.disposed is True
        assert connection.run_sync_calls

    @pytest.mark.asyncio
    async def test_create_full_schema_within_transaction_uses_session_factory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Encadeia criação de schema e abertura de sessão transacional."""
        created: list[str | None] = []
        received_kwargs: list[dict[str, Any]] = []

        async def fake_create_schema(schema_id: str | None) -> None:
            created.append(schema_id)

        async def fake_session_factory(**kwargs: Any) -> FakeAsyncSession:
            received_kwargs.append(kwargs)
            return FakeAsyncSession()

        monkeypatch.setattr(
            schema_handlers, "create_schema_and_tables", fake_create_schema
        )

        session = await schema_handlers.create_full_schema_within_transaction(
            session_factory=fake_session_factory,
            schema_id=UUID(str(uuid7.create())),
        )

        assert isinstance(session, FakeAsyncSession)
        assert created and isinstance(created[0], UUID)
        assert received_kwargs == [
            {
                "read_only": False,
                "schema": str(created[0]),
                "force_create_engine": True,
            }
        ]
