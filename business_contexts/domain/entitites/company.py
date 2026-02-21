"""Módulo da entidade de leitura Company."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.entities import AuditReadBase


@dataclass(frozen=True, kw_only=True)
class Company(AuditReadBase):
    """Entidade de leitura que representa uma empresa."""

    id: UUID
    legal_name: str
    responsible_name: str
    email: str
    cpf: str
    trade_name: str | None = None
    cnpj: str | None = None
