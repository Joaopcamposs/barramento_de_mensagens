"""Módulo de eventos do domínio User."""

from dataclasses import dataclass
from uuid import UUID

from business_contexts.consts import FIRST_USER_CPF, FIRST_USER_PASSWORD
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


@dataclass
class TimeToCreateInitialCompanyUser(Event):
    """Evento emitido para criar o usuário inicial de uma empresa recém-criada."""

    company: UUID
    name: str
    email: str
    cpf: str
    password: str
    active: bool
    admin: bool


@dataclass(kw_only=True)
class TimeToCreateCompanyAdminUser(Event):
    """Evento emitido para criar o usuário administrador padrão de uma empresa."""

    company: UUID
    email: str
    name: str = "Admin User"
    cpf: str = FIRST_USER_CPF
    password: str = FIRST_USER_PASSWORD
    active: bool = True
    admin: bool = True
