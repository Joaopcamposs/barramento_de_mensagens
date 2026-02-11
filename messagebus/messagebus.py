import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NewType

import sentry_sdk

from messagebus.unity_of_work import AbstractUnitOfWork

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


@dataclass
class Command:
    """Classe base para todos os comandos do sistema."""

    pass


@dataclass(kw_only=True)
class Event:
    """Classe base para todos os eventos do sistema."""

    execute_async: bool = False


Message = Command | Event


EventHandlers = NewType("EventHandlers", dict[type[Event], list[Callable]])

CommandHandlers = NewType("CommandHandlers", dict[type[Command], Callable])


class MessageBus:
    """
    Barramento de mensagens que roteia comandos e eventos para seus handlers.

    Processa uma mensagem por vez, coletando novos eventos gerados durante
    o processamento e adicionando-os à fila.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        event_handlers: EventHandlers,
        command_handlers: CommandHandlers,
        raise_event_errors: bool = True,
    ) -> None:
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.raise_event_errors = raise_event_errors
        self.queue: list[Message] = []

    async def handle(self, message: Message) -> Any | None:
        """
        Processa uma mensagem (comando ou evento).

        Args:
            message: Comando ou Evento a ser processado.

        Returns:
            Resultado do comando, se a mensagem for um comando.
        """
        self.queue = [message]
        command_result: Any | None = None

        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, Event):
                await self._handle_event(message)
            elif isinstance(message, Command):
                command_result = await self._handle_command(message)
            else:
                raise TypeError(f"{message} is not an Event or Command")

        return command_result

    async def _handle_event(self, event: Event) -> None:
        """Processa um evento, delegando para os handlers registrados."""
        for handler in self.event_handlers.get(type(event), []):
            try:
                logger.debug(f"Processing event {event} with handler {handler}")
                await handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception as error:
                logger.exception(f"Error processing event {event}")
                self._handle_event_error(error)

    def _handle_event_error(self, error: Exception) -> None:
        """Trata erros de processamento de eventos."""
        if self.raise_event_errors or os.getenv("TEST_ENV") == "true":
            raise error

        if os.getenv("ENV_CONFIG", "development") in ["alpha", "prod"]:
            sentry_sdk.capture_exception(error)

    async def _handle_command(self, command: Command) -> Any | None:
        """Processa um comando, delegando para o handler registrado."""
        logger.debug(f"Processing command {command}")
        try:
            handler = self.command_handlers[type(command)]
            result = await handler(command)
            self.queue.extend(self.uow.collect_new_events())
            return result
        except Exception as error:
            logger.exception(f"Error processing command {command}")
            raise error
