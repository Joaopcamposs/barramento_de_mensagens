"""Módulo do agregado Company."""

from dataclasses import dataclass
from uuid import UUID

import uuid7

from messagebus.entities import Aggregate, OperationType
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyUpdated,
    CompanyDeleted,
)


@dataclass
class Company(Aggregate):
    """Agregado que representa uma empresa no domínio."""

    id: UUID
    name: str
    deleted: bool = False

    def __hash__(self) -> int:
        return hash(self.id)

    @staticmethod
    def create_aggregate(name: str) -> "Company":
        """
        Cria uma nova instância do agregado Company.

        Args:
            name: Nome da empresa.

        Returns:
            Nova instância de Company com ID gerado.
        """
        return Company(id=uuid7.create(), name=name, deleted=False)

    def create(self) -> None:
        """Marca o agregado para inserção e emite evento de criação."""
        self._operation_type = OperationType.INSERT

        self.add_event(
            CompanyCreated(
                id=self.id,
            )
        )

    def update(self, new_name: str) -> None:
        """
        Atualiza o nome da empresa e emite evento de atualização.

        Args:
            new_name: Novo nome da empresa.
        """
        self._operation_type = OperationType.UPDATE

        self.name = new_name

        self.add_event(
            CompanyUpdated(
                id=self.id,
            )
        )

    def delete(self) -> None:
        """Marca o agregado como deletado (soft delete) e emite evento de exclusão."""
        self._operation_type = OperationType.DELETE

        self.deleted = True

        self.add_event(
            CompanyDeleted(
                id=self.id,
            )
        )
