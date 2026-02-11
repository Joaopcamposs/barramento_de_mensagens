"""Módulo de comandos do domínio User."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.messagebus import Command


@dataclass
class CreateUser(Command):
    """Comando para criar um novo usuário."""

    company: UUID
    email: str
    password: str


@dataclass
class UpdateUser(Command):
    """Comando para atualizar um usuário existente."""

    email: str
    new_email: str | None = None
    new_password: str | None = None


@dataclass
class DeleteUser(Command):
    """Comando para excluir um usuário."""

    email: str
