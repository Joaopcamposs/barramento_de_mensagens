"""Módulo de comandos de autenticação e segurança."""

from dataclasses import dataclass

from messagebus.messagebus import Command


@dataclass(frozen=True)
class AuthenticateUser(Command):
    """Comando para autenticar um usuário com email e senha."""

    email: str
    password: str
