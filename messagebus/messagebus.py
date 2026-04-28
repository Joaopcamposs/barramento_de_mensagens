from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass
from typing import NewType, TypeVar
import sentry_sdk

from libs.consts import IS_ALPHA, IS_PROD, IS_TEST
from libs.logger import logger
from messagebus.unity_of_work import AbstractUnitOfWork


SENSITIVE_FIELD_MARKERS = (
    "password",
    "senha",
    "token",
    "secret",
    "api_key",
    "apikey",
    "reset_link",
    "authorization",
)


def _is_sensitive_field(field_name: str) -> bool:
    """Indica se o nome do campo sugere conteúdo sensível que deve ser mascarado."""
    normalized_field_name = field_name.casefold()
    return any(marker in normalized_field_name for marker in SENSITIVE_FIELD_MARKERS)


def _safe_message_repr(message: object) -> str:
    """Serializa mensagens de forma segura, mascarando campos sensíveis."""
    if not is_dataclass(message):
        return repr(message)

    parts: list[str] = []
    for field_info in fields(message):
        field_name = field_info.name
        field_value = getattr(message, field_name)
        if _is_sensitive_field(field_name):
            parts.append(f"{field_name}=***")
            continue
        parts.append(f"{field_name}={field_value!r}")

    return f"{type(message).__name__}({', '.join(parts)})"


@dataclass(frozen=True)
class Command:
    """Classe base para todos os comandos do sistema."""

    def __str__(self) -> str:
        """Retorna uma representação segura para logging."""
        return _safe_message_repr(self)


@dataclass(kw_only=True, frozen=True)
class Event:
    """Classe base para todos os eventos do sistema."""

    execute_async: bool = False

    def __str__(self) -> str:
        """Retorna uma representação segura para logging."""
        return _safe_message_repr(self)


Message = Command | Event


EventHandlers = NewType("EventHandlers", dict[type[Event], list[Callable]])

CommandHandlers = NewType("CommandHandlers", dict[type[Command], Callable])

CommandResult = TypeVar("CommandResult")


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
        """Configura o barramento com o UoW e os handlers registrados."""
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.raise_event_errors = raise_event_errors
        self.queue: list[Message] = []

    async def handle(self, message: Message) -> CommandResult | None:
        """
        Processa uma mensagem (comando ou evento).

        Args:
            message: Comando ou Evento a ser processado.

        Returns:
            Resultado do comando, se a mensagem for um comando.
        """
        self.queue = [message]
        command_result: CommandResult | None = None

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
                logger.debug(
                    f"Processing event {type(event).__name__} with handler {handler}"
                )
                await handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception as error:
                logger.exception(f"Error processing event {type(event).__name__}")
                self._handle_event_error(error)

    def _handle_event_error(self, error: Exception) -> None:
        """Trata erros de processamento de eventos."""
        if self.raise_event_errors or IS_TEST:
            raise error

        if IS_ALPHA or IS_PROD:
            sentry_sdk.capture_exception(error)

    async def _handle_command(self, command: Command) -> CommandResult | None:
        """Processa um comando, delegando para o handler registrado."""
        logger.debug(f"Processing command {type(command).__name__}")
        try:
            handler = self.command_handlers[type(command)]
            result = await handler(command)
            self.queue.extend(self.uow.collect_new_events())
            return result
        except Exception as error:
            logger.exception(f"Error processing command {type(command).__name__}")
            raise error
