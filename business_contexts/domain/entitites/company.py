"""Módulo da entidade de leitura Company."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Company:
    """Entidade de leitura que representa uma empresa."""

    id: UUID
    name: str
