"""Módulo do agregado User."""

from dataclasses import dataclass
from uuid import UUID
import uuid7

from messagebus.entities import Aggregate, OperationType
from business_contexts.domain.events.user import (
    UserCreated,
    UserUpdated,
    UserDeleted,
)


@dataclass
class User(Aggregate):
    """Agregado que representa um usuário no domínio."""

    id: UUID
    company: UUID
    email: str
    password: str

    def __hash__(self) -> int:
        return hash(self.id)

    @staticmethod
    def create_aggregate(company: UUID, email: str, password: str) -> "User":
        """
        Cria uma nova instância do agregado User.

        Args:
            company: ID da empresa associada.
            email: Email do usuário.
            password: Senha do usuário.

        Returns:
            Nova instância de User com ID gerado.
        """
        return User(
            id=uuid7.create(),
            company=company,
            email=email,
            password=password,
        )

    def create(self) -> None:
        """Marca o agregado para inserção e emite evento de criação."""
        self._operation_type = OperationType.INSERT

        self.add_event(
            UserCreated(
                id=self.id,
                company=self.company,
            )
        )

    def update(self, email: str | None = None, password: str | None = None) -> None:
        """
        Atualiza os dados do usuário e emite evento de atualização.

        Args:
            email: Novo email (opcional).
            password: Nova senha (opcional).
        """
        self._operation_type = OperationType.UPDATE

        if email is not None:
            self.email = email
        if password is not None:
            self.password = password

        self.add_event(
            UserUpdated(
                id=self.id,
                company=self.company,
            )
        )

    def delete(self) -> None:
        """Marca o agregado para remoção e emite evento de exclusão."""
        self._operation_type = OperationType.DELETE

        self.add_event(
            UserDeleted(
                id=self.id,
                company=self.company,
            )
        )
