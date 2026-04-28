"""Testes unitários do contexto de barramento de mensagens e UoW."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
import uuid7

from business_contexts.domains import Domain
from business_contexts.domain.excecoes import CredentialsException
from business_contexts.adapters.repository.domain_repo.user import UserDomainRepo
from business_contexts.adapters.repository.view_repo.user import UserViewRepo
from messagebus.bootstrap import bootstrap_base
from messagebus.entities import (
    Aggregate,
    DomainRepository,
    OperationType,
    ViewRepository,
)
from messagebus.messagebus import Command, CommandHandlers, Event, EventHandlers
from messagebus.unity_of_work import (
    UnitOfWork,
    UnitOfWorkWithProblem,
)
from tests.unit.helpers import FakeAsyncSession


class TestBootstrapBase:
    """Testes para bootstrap base e injeção de dependências."""

    @pytest.mark.asyncio
    async def test_bootstrap_base_injects_uow_on_handlers(self) -> None:
        """Verifica a injeção de dependência de UoW em handlers registrados."""

        @dataclass(frozen=True)
        class FakeCommand(Command):
            value: str

        @dataclass(kw_only=True, frozen=True)
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

        @dataclass(kw_only=True, frozen=True)
        class DemoEvent(Event):
            id: Any

        aggregate = DemoAggregate(id=uuid7.create())
        aggregate._operation_type = OperationType.INSERT

        event = DemoEvent(id=aggregate.id)
        aggregate.add_event(event)

        assert aggregate.operation_type == OperationType.INSERT
        assert aggregate.events == [event]


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
        assert read_session.closed is True
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
    async def test_collect_new_events_yields_events_from_seen_aggregates(self) -> None:
        """Coleta eventos pendentes dos agregados rastreados no repositório."""

        @dataclass(kw_only=True, frozen=True)
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
    async def test_collect_new_events_yields_events_without_aggregate(self) -> None:
        """Coleta eventos registrados diretamente na UoW, sem agregado."""

        @dataclass(kw_only=True, frozen=True)
        class DemoEvent(Event):
            name: str

        uow = UnitOfWork(
            session_factory=lambda **_: FakeAsyncSession(), schema="tenant-d"
        )
        uow.add_events_without_aggregate(DemoEvent(name="detached"))

        collected = list(uow.collect_new_events())

        assert [event.name for event in collected] == ["detached"]

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
    async def test_unit_of_work_read_only_opens_only_read_session(self) -> None:
        """Em modo somente leitura, abre apenas sessão de leitura e view_repo."""
        read_session = FakeAsyncSession()
        calls: list[bool] = []

        async def session_factory(read_only: bool, **_: Any) -> FakeAsyncSession:
            calls.append(read_only)
            return read_session

        uow = UnitOfWork(
            session_factory=session_factory, schema="tenant-read", read_only=True
        )
        uow(Domain.user)

        async with uow:
            assert uow.session is None
            assert isinstance(uow.view_repo.session, FakeAsyncSession)

        assert calls == [True]
        assert read_session.closed is True

    @pytest.mark.asyncio
    async def test_unit_of_work_get_repo_helpers_validate_types(self) -> None:
        """Retorna repositórios tipados e falha quando o tipo esperado diverge."""
        write_session = FakeAsyncSession()
        read_session = FakeAsyncSession()

        async def session_factory(read_only: bool, **_: Any) -> FakeAsyncSession:
            return read_session if read_only else write_session

        uow = UnitOfWork(session_factory=session_factory, schema="tenant-helper")
        uow(Domain.user)

        async with uow:
            assert isinstance(uow.get_domain_repo(UserDomainRepo), UserDomainRepo)
            assert isinstance(uow.get_view_repo(UserViewRepo), UserViewRepo)
            with pytest.raises(TypeError):
                uow.get_domain_repo(UserViewRepo)  # type: ignore[type-var]

    def test_require_user_id_raises_without_user(self) -> None:
        """Garante erro de credenciais quando não há usuário autenticado."""
        uow = UnitOfWork(session_factory=lambda **_: FakeAsyncSession(), schema="tenant")

        with pytest.raises(CredentialsException):
            uow.require_user_id()
