"""Módulo de comandos do domínio User."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.messagebus import Command


@dataclass(frozen=True)
class CreateUser(Command):
    """Comando para criar um novo usuário."""

    company: UUID
    email: str
    cpf: str
    password: str
    active: bool = True
    admin: bool = False


@dataclass(frozen=True)
class UpdateUser(Command):
    """Comando para atualizar um usuário existente."""

    email: str
    new_email: str | None = None
    new_password: str | None = None
    new_active: bool | None = None
    new_admin: bool | None = None


@dataclass(frozen=True)
class DeleteUser(Command):
    """Comando para excluir um usuário."""

    email: str
