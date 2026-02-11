"""Módulo de comandos do domínio User."""

from dataclasses import dataclass

from messagebus.messagebus import Command


@dataclass
class CreateUser(Command):
    """Comando para criar um novo usuário."""

    email: str
    cpf: str
    password: str
    active: bool = True
    admin: bool = False


@dataclass
class UpdateUser(Command):
    """Comando para atualizar um usuário existente."""

    email: str
    new_email: str | None = None
    new_password: str | None = None
    new_active: bool | None = None
    new_admin: bool | None = None


@dataclass
class DeleteUser(Command):
    """Comando para excluir um usuário."""

    email: str
