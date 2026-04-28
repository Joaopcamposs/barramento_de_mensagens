"""Módulo de eventos do domínio User."""

from dataclasses import dataclass
from uuid import UUID

from libs.consts import FIRST_USER_CPF, FIRST_USER_PASSWORD
from messagebus.entities import AuditableEvent
from messagebus.messagebus import Event


@dataclass(kw_only=True, frozen=True)
class UserCreated(AuditableEvent, Event):
    """Evento emitido quando um usuário é criado."""

    id: UUID
    company: UUID


@dataclass(kw_only=True, frozen=True)
class UserUpdated(AuditableEvent, Event):
    """Evento emitido quando um usuário é atualizado."""

    id: UUID
    company: UUID


@dataclass(kw_only=True, frozen=True)
class UserDeleted(AuditableEvent, Event):
    """Evento emitido quando um usuário é excluído."""

    id: UUID
    company: UUID


@dataclass(frozen=True)
class TimeToCreateInitialCompanyUser(Event):
    """Evento emitido para criar o usuário inicial de uma empresa recém-criada."""

    company: UUID
    name: str
    email: str
    cpf: str
    password: str
    active: bool
    admin: bool


@dataclass(kw_only=True, frozen=True)
class TimeToCreateCompanyAdminUser(Event):
    """Evento emitido para criar o usuário administrador padrão de uma empresa."""

    company: UUID
    email: str
    name: str = "Admin User"
    cpf: str = FIRST_USER_CPF
    password: str = FIRST_USER_PASSWORD
    active: bool = True
    admin: bool = True
