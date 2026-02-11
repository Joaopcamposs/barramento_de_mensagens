"""Módulo do agregado User."""

from dataclasses import dataclass
from uuid import UUID
import uuid7

from messagebus.entities import Aggregate, OperationType, UserSecurity
from business_contexts.domain.events.user import (
    UserCreated,
    UserUpdated,
    UserDeleted,
)


@dataclass(kw_only=True)
class User(Aggregate, UserSecurity):
    """Agregado que representa um usuário no domínio."""

    id: UUID
    company: UUID
    email: str
    cpf: str
    password: str
    active: bool
    admin: bool

    def __hash__(self) -> int:
        return hash(self.id)

    @staticmethod
    def create_aggregate(
        company: UUID,
        email: str,
        cpf: str,
        password: str,
        active: bool = True,
        admin: bool = False,
    ) -> "User":
        """
        Cria uma nova instância do agregado User.

        Args:
            company: ID da empresa associada.
            email: Email do usuário.
            cpf: CPF do usuário.
            password: Senha do usuário.
            active: Se o usuário está ativo.
            admin: Se o usuário é administrador.

        Returns:
            Nova instância de User com ID gerado.
        """
        return User(
            id=uuid7.create(),
            company=company,
            email=email,
            cpf=cpf,
            password=password,
            active=active,
            admin=admin,
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

    def update(
        self,
        email: str | None = None,
        password: str | None = None,
        active: bool | None = None,
        admin: bool | None = None,
    ) -> None:
        """
        Atualiza os dados do usuário e emite evento de atualização.

        Args:
            email: Novo email (opcional).
            password: Nova senha (opcional).
            active: Novo status de ativação (opcional).
            admin: Novo status de administrador (opcional).
        """
        self._operation_type = OperationType.UPDATE

        if email is not None:
            self.email = email
        if password is not None:
            self.password = password
        if active is not None:
            self.active = active
        if admin is not None:
            self.admin = admin

        self.add_event(
            UserUpdated(
                id=self.id,
                company=self.company,
            )
        )

    def delete(self) -> None:
        """Marca o agregado como deletado (soft delete) e emite evento de exclusão."""
        self._operation_type = OperationType.DELETE

        self.deleted = True

        self.add_event(
            UserDeleted(
                id=self.id,
                company=self.company,
            )
        )
