"""Módulo de comandos do domínio Company."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.messagebus import Command


@dataclass
class CreateCompany(Command):
    """Comando para criar uma nova empresa."""

    legal_name: str
    responsible_name: str
    active: bool
    cpf: str
    email: str
    password: str
    cnpj: str | None = None
    trade_name: str | None = None
    should_create_user: bool = True

    _first_company_id: UUID | None = None

    @property
    def first_company_id(self) -> UUID | None:
        return self._first_company_id


@dataclass
class UpdateCompany(Command):
    """Comando para atualizar uma empresa existente."""

    legal_name: str
    new_legal_name: str | None = None
    new_trade_name: str | None = None
    new_responsible_name: str | None = None
    new_email: str | None = None
    new_active: bool | None = None


@dataclass
class DeleteCompany(Command):
    """Comando para excluir uma empresa."""

    legal_name: str
