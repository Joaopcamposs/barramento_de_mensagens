"""Módulo da entidade de leitura User."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class User:
    """Entidade de leitura que representa um usuário."""

    id: UUID
    company: UUID
    email: str
    deleted: bool
