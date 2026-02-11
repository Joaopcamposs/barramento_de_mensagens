"""Módulo de comandos do domínio Company."""

from dataclasses import dataclass

from messagebus.messagebus import Command


@dataclass
class CreateCompany(Command):
    """Comando para criar uma nova empresa."""

    name: str


@dataclass
class UpdateCompany(Command):
    """Comando para atualizar uma empresa existente."""

    name: str
    new_name: str


@dataclass
class DeleteCompany(Command):
    """Comando para excluir uma empresa."""

    name: str
