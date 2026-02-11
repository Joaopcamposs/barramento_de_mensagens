"""Testes unitários para o barramento de mensagens e bootstrap."""

from dataclasses import dataclass

import pytest

from messagebus.entities import OperationType
from messagebus.messagebus import (
    Command,
    CommandHandlers,
    Event,
    EventHandlers,
    MessageBus,
)


class FakeUnitOfWork:
    """Fake do Unit of Work para testes unitários."""

    def __init__(self) -> None:
        self.committed = False
        self._events: list[Event] = []

    def collect_new_events(self) -> list[Event]:
        """Retorna e limpa a lista de eventos pendentes."""
        events = self._events[:]
        self._events.clear()
        return events

    def add_event(self, event: Event) -> None:
        """Adiciona um evento à fila."""
        self._events.append(event)


@dataclass
class FakeCommand(Command):
    """Comando fake para testes."""

    value: str


@dataclass
class FakeEvent(Event):
    """Evento fake para testes."""

    value: str


class TestMessageBus:
    """Testes para o MessageBus."""

    @pytest.fixture
    def uow(self) -> FakeUnitOfWork:
        """Cria um fake UoW para testes."""
        return FakeUnitOfWork()

    async def test_handle_command_returns_result(self, uow: FakeUnitOfWork) -> None:
        """Verifica que handle() retorna o resultado do command handler."""

        async def handler(command: FakeCommand) -> str:
            return f"handled: {command.value}"

        bus = MessageBus(
            uow=uow,
            event_handlers=EventHandlers({}),
            command_handlers=CommandHandlers({FakeCommand: handler}),
        )

        result = await bus.handle(FakeCommand(value="test"))
        assert result == "handled: test"

    async def test_handle_event_calls_all_handlers(self, uow: FakeUnitOfWork) -> None:
        """Verifica que handle() chama todos os handlers do evento."""
        results: list[str] = []

        async def handler1(event: FakeEvent) -> None:
            results.append(f"handler1: {event.value}")

        async def handler2(event: FakeEvent) -> None:
            results.append(f"handler2: {event.value}")

        bus = MessageBus(
            uow=uow,
            event_handlers=EventHandlers({FakeEvent: [handler1, handler2]}),
            command_handlers=CommandHandlers({}),
        )

        await bus.handle(FakeEvent(value="test"))
        assert len(results) == 2
        assert "handler1: test" in results
        assert "handler2: test" in results

    async def test_handle_unknown_message_raises_type_error(
        self, uow: FakeUnitOfWork
    ) -> None:
        """Verifica que handle() lança TypeError para mensagens desconhecidas."""
        bus = MessageBus(
            uow=uow,
            event_handlers=EventHandlers({}),
            command_handlers=CommandHandlers({}),
        )

        with pytest.raises(TypeError):
            await bus.handle("not a message")  # type: ignore

    async def test_command_handler_exception_propagates(
        self, uow: FakeUnitOfWork
    ) -> None:
        """Verifica que exceções de command handlers são propagadas."""

        async def failing_handler(command: FakeCommand) -> None:
            raise ValueError("command error")

        bus = MessageBus(
            uow=uow,
            event_handlers=EventHandlers({}),
            command_handlers=CommandHandlers({FakeCommand: failing_handler}),
        )

        with pytest.raises(ValueError, match="command error"):
            await bus.handle(FakeCommand(value="test"))

    async def test_event_handler_exception_propagates_when_configured(
        self, uow: FakeUnitOfWork
    ) -> None:
        """Verifica que exceções de event handlers são propagadas quando configurado."""

        async def failing_handler(event: FakeEvent) -> None:
            raise ValueError("event error")

        bus = MessageBus(
            uow=uow,
            event_handlers=EventHandlers({FakeEvent: [failing_handler]}),
            command_handlers=CommandHandlers({}),
            raise_event_errors=True,
        )

        with pytest.raises(ValueError, match="event error"):
            await bus.handle(FakeEvent(value="test"))

    async def test_queue_processes_events_from_command(self, uow: FakeUnitOfWork) -> None:
        """Verifica que eventos gerados por comandos são processados."""
        event_results: list[str] = []

        async def command_handler(command: FakeCommand) -> str:
            uow.add_event(FakeEvent(value="from_command"))
            return "ok"

        async def event_handler(event: FakeEvent) -> None:
            event_results.append(event.value)

        bus = MessageBus(
            uow=uow,
            event_handlers=EventHandlers({FakeEvent: [event_handler]}),
            command_handlers=CommandHandlers({FakeCommand: command_handler}),
        )

        result = await bus.handle(FakeCommand(value="trigger"))
        assert result == "ok"
        assert "from_command" in event_results


class TestOperationType:
    """Testes para o enum OperationType."""

    def test_insert_value(self) -> None:
        """Verifica o valor do tipo INSERT."""
        assert OperationType.INSERT.value == "insert"

    def test_update_value(self) -> None:
        """Verifica o valor do tipo UPDATE."""
        assert OperationType.UPDATE.value == "update"

    def test_delete_value(self) -> None:
        """Verifica o valor do tipo DELETE."""
        assert OperationType.DELETE.value == "delete"
