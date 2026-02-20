from messagebus.bootstrap import bootstrap_base
from messagebus.entities import UserBase
from messagebus.messagebus import MessageBus, EventHandlers, CommandHandlers
from messagebus.unity_of_work import AbstractUnitOfWork, UnitOfWork


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
    from business_contexts.handlers import COMMAND_HANDLERS, EVENT_HANDLERS

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
