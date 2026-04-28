"""Módulo da entidade de leitura User."""

from dataclasses import dataclass
from uuid import UUID

from libs.security import UserSecurity
from messagebus.entities import AuditBase, UserBase


@dataclass(kw_only=True)
class User(AuditBase, UserBase, UserSecurity):
    """Entidade de leitura que representa um usuário."""

    id: UUID
    company: UUID
    email: str
    cpf: str
    admin: bool


@dataclass(kw_only=True)
class PublicUser(UserSecurity):
    """Entidade de leitura que representa um usuário público para roteamento de tenant."""

    id: UUID
    company: UUID
    email_encrypted: bytes
    email_lookup_hmac: str
    cpf_lookup_hmac: str | None
