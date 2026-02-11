"""Módulo de eventos do domínio User."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.messagebus import Event


@dataclass
class UserCreated(Event):
    """Evento emitido quando um usuário é criado."""

    id: UUID
    company: UUID


@dataclass
class UserUpdated(Event):
    """Evento emitido quando um usuário é atualizado."""

    id: UUID
    company: UUID


@dataclass
class UserDeleted(Event):
    """Evento emitido quando um usuário é excluído."""

    id: UUID
    company: UUID
