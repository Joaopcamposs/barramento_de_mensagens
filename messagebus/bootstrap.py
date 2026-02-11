"""Módulo de bootstrap para configuração e inicialização do barramento de mensagens."""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from messagebus.entities import UserBase
from messagebus.messagebus import (
    Command,
    CommandHandlers,
    Event,
    EventHandlers,
    MessageBus,
)
from messagebus.unity_of_work import AbstractUnitOfWork, UnitOfWork


def bootstrap_base(
    uow: AbstractUnitOfWork,
    command_handlers: CommandHandlers,
    event_handlers: EventHandlers,
    raise_event_errors: bool = False,
) -> MessageBus:
    """
    Configura o barramento de mensagens com injeção de dependências.

    Args:
        uow: Instância do Unit of Work.
        command_handlers: Mapa de comandos para handlers.
        event_handlers: Mapa de eventos para handlers.
        raise_event_errors: Se True, propaga exceções de handlers de evento.

    Returns:
        Instância configurada do MessageBus.
    """
    dependencies: dict[str, Any] = {"uow": uow}

    injected_event_handlers = EventHandlers(
        {
            event_type: [
                inject_dependencies(handler, dependencies) for handler in event_handlers
            ]
            for event_type, event_handlers in event_handlers.items()
        }
    )
    injected_command_handlers = CommandHandlers(
        {
            command_type: inject_dependencies(handler, dependencies)
            for command_type, handler in command_handlers.items()
        }
    )

    return MessageBus(
        uow=uow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
        raise_event_errors=raise_event_errors,
    )


def inject_dependencies(handler: Callable, dependencies: dict[str, Any]) -> Callable:
    """
    Injeta dependências em um handler baseado nos parâmetros da sua assinatura.

    Args:
        handler: Função handler a receber as dependências.
        dependencies: Dicionário de dependências disponíveis.

    Returns:
        Wrapper assíncrono com dependências injetadas.
    """
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency for name, dependency in dependencies.items() if name in params
    }

    @functools.wraps(handler)
    async def async_wrapper(message: Command | Event) -> Any:
        try:
            return await handler(message, **deps)
        finally:
            pass

    return async_wrapper


def bootstrap(
    event_handlers: EventHandlers | None = None,
    command_handlers: CommandHandlers | None = None,
    uow: AbstractUnitOfWork | None = None,
    user: UserBase | None = None,
    schema: str | None = None,
    create_schema: bool = False,
    raise_event_errors: bool = False,
    read_only: bool = False,
) -> MessageBus:
    """
    Inicializa o barramento de mensagens com configurações padrão ou customizadas.

    Args:
        event_handlers: Handlers de evento customizados (opcional).
        command_handlers: Handlers de comando customizados (opcional).
        uow: Unit of Work customizado (opcional).
        user: Usuário base para o repositório de domínio (opcional).
        schema: Schema do banco de dados (opcional).
        create_schema: Se True, cria o schema no banco antes de operar.
        raise_event_errors: Se True, propaga exceções de handlers de evento.
        read_only: Se True, cria Unit of Work somente leitura.

    Returns:
        Instância configurada do MessageBus.
    """
    from messagebus.handlers import COMMAND_HANDLERS, EVENT_HANDLERS

    command_handlers = command_handlers or COMMAND_HANDLERS
    event_handlers = event_handlers or EVENT_HANDLERS

    if uow is None:
        uow = UnitOfWork(
            user=user,
            schema=schema,
            create_schema=create_schema,
            read_only=read_only,
        )

    return bootstrap_base(
        uow=uow,
        event_handlers=event_handlers,
        command_handlers=command_handlers,
        raise_event_errors=raise_event_errors,
    )
