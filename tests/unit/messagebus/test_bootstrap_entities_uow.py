"""Testes unitários do contexto de barramento de mensagens e UoW."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
import uuid7

from business_contexts.domains import Domain
from messagebus.bootstrap import bootstrap_base, inject_dependencies
from messagebus.entities import (
    Aggregate,
    AuditReadBase,
    DomainRepository,
    OperationType,
    ViewRepository,
)
from messagebus.messagebus import (
    Command,
    CommandHandlers,
    Event,
    EventHandlers,
    MessageBus,
)
from messagebus.unity_of_work import (
    UnitOfWork,
    UnitOfWorkContextAlreadyOpen,
    UnitOfWorkWithProblem,
)
from tests.unit.helpers import FakeAsyncSession


class TestBootstrapBase:
    """Testes para bootstrap base e injeção de dependências."""

    @pytest.mark.asyncio
    async def test_bootstrap_base_injects_uow_on_handlers(self) -> None:
        """Verifica a injeção de dependência de UoW em handlers registrados."""

        @dataclass
        class FakeCommand(Command):
            value: str

        @dataclass(kw_only=True)
        class FakeEvent(Event):
            value: str

        class FakeUow:
            def __init__(self) -> None:
                self.calls = 0

            def collect_new_events(self) -> list[Event]:
                self.calls += 1
                return []

        async def command_handler(command: FakeCommand, uow: FakeUow) -> str:
            return f"{command.value}:{uow.calls}"

        received: list[str] = []

        async def event_handler(event: FakeEvent, uow: FakeUow) -> None:
            received.append(f"{event.value}:{uow.calls}")

        uow = FakeUow()
        bus = bootstrap_base(
            uow=uow,  # type: ignore[arg-type]
            command_handlers=CommandHandlers({FakeCommand: command_handler}),
            event_handlers=EventHandlers({FakeEvent: [event_handler]}),
        )

        result = await bus.handle(FakeCommand("ok"))
        await bus.handle(FakeEvent(value="evt"))

        assert result == "ok:0"
        assert received == ["evt:1"]

    @pytest.mark.asyncio
    async def test_inject_dependencies_ignores_unneeded_deps(self) -> None:
        """Garante que apenas parâmetros compatíveis são injetados no wrapper."""

        @dataclass
        class FakeCommand(Command):
            value: str

        async def handler(command: FakeCommand) -> str:
            return command.value

        wrapped = inject_dependencies(handler, {"uow": object(), "unused": object()})

        result = await wrapped(FakeCommand("value"))
        assert result == "value"


class TestMessageBusErrorPaths:
    """Testes dos caminhos de erro do MessageBus."""

    @pytest.mark.asyncio
    async def test_handle_event_error_sends_exception_to_sentry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valida captura em Sentry quando ambiente é produtivo e erro não é propagado."""
        captured: list[Exception] = []

        monkeypatch.setenv("TEST_ENV", "false")
        monkeypatch.setenv("ENV_CONFIG", "prod")
        monkeypatch.setattr(
            "messagebus.messagebus.sentry_sdk.capture_exception",
            lambda error: captured.append(error),
        )

        bus = MessageBus(
            uow=SimpleNamespace(collect_new_events=lambda: []),
            event_handlers=EventHandlers({}),
            command_handlers=CommandHandlers({}),
            raise_event_errors=False,
        )

        error = RuntimeError("boom")
        bus._handle_event_error(error)

        assert captured == [error]


class TestEntityBaseClasses:
    """Testes das classes base de entidades."""

    def test_repositories_store_session_when_provided(self) -> None:
        """Confirma que os repositórios base guardam a sessão recebida."""
        session = FakeAsyncSession()
        domain_repo = DomainRepository(session=session)  # type: ignore[abstract]
        view_repo = ViewRepository(session=session)  # type: ignore[abstract]

        assert domain_repo.session is session
        assert view_repo.session is session

    def test_aggregate_add_event_and_operation_property(self) -> None:
        """Verifica adição de evento e leitura do tipo de operação."""

        @dataclass(kw_only=True)
        class DemoAggregate(Aggregate):
            id: Any

        @dataclass(kw_only=True)
        class DemoEvent(Event):
            id: Any

        aggregate = DemoAggregate(id=uuid7.create())
        aggregate._operation_type = OperationType.INSERT

        event = DemoEvent(id=aggregate.id)
        aggregate.add_event(event)

        assert aggregate.operation_type == OperationType.INSERT
        assert aggregate.events == [event]

    def test_audit_read_base_is_deleted_property(self) -> None:
        """Confirma cálculo de is_deleted na base de leitura imutável."""
        entity = AuditReadBase(deleted_at=None)
        deleted = AuditReadBase(
            deleted_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
        )

        assert entity.is_deleted is False
        assert deleted.is_deleted is True


class TestUnitOfWorkBase:
    """Testes da implementação concreta de UnitOfWork."""

    @pytest.mark.asyncio
    async def test_unit_of_work_rejects_user_outside_schema(self) -> None:
        """Impede abertura da UoW quando usuário não pertence ao schema."""
        user = SimpleNamespace(company=uuid7.create(), id=uuid7.create())
        with pytest.raises(UnitOfWorkWithProblem):
            UnitOfWork(
                session_factory=lambda **_: FakeAsyncSession(),
                user=user,
                schema=str(uuid7.create()),
                create_schema=False,
            )

    @pytest.mark.asyncio
    async def test_unit_of_work_full_lifecycle_commit_and_dispose(self) -> None:
        """Valida fluxo de entrada, commit e liberação de recursos."""
        write_session = FakeAsyncSession()
        read_session = FakeAsyncSession()

        async def session_factory(
            read_only: bool, schema: str | None = None, **_: Any
        ) -> FakeAsyncSession:
            assert schema == "tenant-a"
            return read_session if read_only else write_session

        uow = UnitOfWork(session_factory=session_factory, schema="tenant-a")
        configured = uow(Domain.user)

        assert configured is uow
        assert uow.domain_repo.__name__ == "UserDomainRepo"
        assert uow.view_repo.__name__ == "UserViewRepo"

        async with uow:
            assert isinstance(uow.domain_repo.session, FakeAsyncSession)
            assert isinstance(uow.view_repo.session, FakeAsyncSession)
            await uow.commit()

        assert write_session.committed is True
        assert write_session.closed is True
        assert write_session.bind.disposed is True
        assert read_session.closed is True
        assert read_session.bind.disposed is True
        assert uow.session is None
        assert uow.read_session is None

    @pytest.mark.asyncio
    async def test_unit_of_work_rolls_back_when_not_committed(self) -> None:
        """Executa rollback automático ao sair sem commit."""
        write_session = FakeAsyncSession()
        read_session = FakeAsyncSession()

        async def session_factory(read_only: bool, **_: Any) -> FakeAsyncSession:
            return read_session if read_only else write_session

        uow = UnitOfWork(session_factory=session_factory, schema="tenant-b")
        uow(Domain.company)

        async with uow:
            pass

        assert write_session.rolled_back is True

    @pytest.mark.asyncio
    async def test_unit_of_work_context_cannot_be_opened_twice(self) -> None:
        """Garante erro ao tentar abrir o mesmo contexto de UoW duas vezes."""
        session = FakeAsyncSession()

        async def session_factory(read_only: bool, **_: Any) -> FakeAsyncSession:
            return FakeAsyncSession() if read_only else session

        uow = UnitOfWork(session_factory=session_factory, schema="tenant-c")
        uow.domain_repo = None  # type: ignore[assignment]
        uow.view_repo = None  # type: ignore[assignment]

        await uow.__aenter__()
        with pytest.raises(UnitOfWorkContextAlreadyOpen):
            await uow.__aenter__()
        await uow.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_collect_new_events_yields_events_from_seen_aggregates(self) -> None:
        """Coleta eventos pendentes dos agregados rastreados no repositório."""

        @dataclass(kw_only=True)
        class DemoEvent(Event):
            name: str

        @dataclass(kw_only=True)
        class DemoAggregate(Aggregate):
            id: Any

        aggregate = DemoAggregate(id=uuid7.create())
        aggregate.events.extend([DemoEvent(name="a"), DemoEvent(name="b")])

        uow = UnitOfWork(
            session_factory=lambda **_: FakeAsyncSession(), schema="tenant-d"
        )
        uow.domain_repo = SimpleNamespace(seen=[aggregate])

        collected = list(uow.collect_new_events())

        assert [event.name for event in collected] == ["a", "b"]
        assert aggregate.events == []

    @pytest.mark.asyncio
    async def test_unit_of_work_create_schema_branch_uses_schema_builder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre caminho de criação de schema completo antes de iniciar sessão."""
        write_session = FakeAsyncSession()
        read_session = FakeAsyncSession()
        builder_calls: list[tuple[Any, Any]] = []

        async def session_factory(read_only: bool, **_: Any) -> FakeAsyncSession:
            return read_session if read_only else write_session

        async def fake_builder(
            session_factory: Any, schema_id: str | None
        ) -> FakeAsyncSession:
            builder_calls.append((session_factory, schema_id))
            return write_session

        monkeypatch.setattr(
            "infra.database.schema_handlers.create_full_schema_within_transaction",
            fake_builder,
        )

        uow = UnitOfWork(
            session_factory=session_factory,
            schema="tenant-e",
            create_schema=True,
        )
        uow(Domain.audit_log)

        async with uow:
            assert uow.create_schema is False

        assert builder_calls == [(session_factory, "tenant-e")]

    @pytest.mark.asyncio
    async def test_user_id_property_returns_none_without_user(self) -> None:
        """Confirma retorno None quando não há usuário autenticado."""
        uow = UnitOfWork(
            session_factory=lambda **_: FakeAsyncSession(), schema="tenant-f"
        )
        assert uow.user_id is None

    @pytest.mark.asyncio
    async def test_explicit_rollback_calls_session_rollback(self) -> None:
        """Valida chamada explícita de rollback."""
        write_session = FakeAsyncSession()
        read_session = FakeAsyncSession()

        async def session_factory(read_only: bool, **_: Any) -> FakeAsyncSession:
            return read_session if read_only else write_session

        uow = UnitOfWork(session_factory=session_factory, schema="tenant-g")
        uow(Domain.user)

        async with uow:
            await uow.rollback()

        assert write_session.rolled_back is True

    def test_unit_of_work_uses_default_session_factory_when_not_provided(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre caminho que importa factory padrão da infraestrutura."""

        async def fake_default_factory(**_: Any) -> FakeAsyncSession:
            return FakeAsyncSession()

        monkeypatch.setattr(
            "infra.database.default_async_sql_session_factory", fake_default_factory
        )

        uow = UnitOfWork(schema="tenant-h")

        assert uow.sql_session_factory is fake_default_factory
