"""Módulo da entidade de leitura Company."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Company:
    """Entidade de leitura que representa uma empresa."""

    id: UUID
    legal_name: str
    responsible_name: str
    email: str
    cpf: str
    active: bool
    deleted: bool
    trade_name: str | None = None
    cnpj: str | None = None
