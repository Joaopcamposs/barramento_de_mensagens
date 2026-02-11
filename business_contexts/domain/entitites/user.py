"""Módulo da entidade de leitura User."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.entities import UserSecurity


@dataclass(kw_only=True)
class User(UserSecurity):
    """Entidade de leitura que representa um usuário."""

    id: UUID
    company: UUID
    email: str
    cpf: str
    active: bool
    admin: bool
    deleted: bool
