"""Módulo do agregado User."""

from dataclasses import dataclass
from uuid import UUID

import uuid7

from business_contexts.domain.value_objects.enums import AuditConstant, EntityType
from business_contexts.domain.events.user import (
    UserCreated,
    UserDeleted,
    UserUpdated,
)
from messagebus.entities import Aggregate, OperationType, UserSecurity


@dataclass(kw_only=True)
class User(Aggregate, UserSecurity):
    """Agregado que representa um usuário no domínio."""

    id: UUID
    company: UUID
    email: str
    cpf: str
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
        hash_password = UserSecurity.encrypt_password(password)

        return User(
            id=uuid7.create(),
            company=company,
            email=email,
            cpf=cpf,
            _password_hash=hash_password,
            active=active,
            admin=admin,
        )

    def create(self, user_id: UUID | None = None) -> None:
        """Marca o agregado para inserção e emite evento de criação."""
        self._operation_type = OperationType.INSERT
        self._set_create_audit(user_id)

        new_data = {
            "email": self.email,
            "cpf": self.cpf,
            "active": self.active,
            "admin": self.admin,
        }

        self.add_event(
            UserCreated(
                id=self.id,
                company=self.company,
                entity_type=EntityType.USER,
                new_data=new_data,
            )
        )

    def update(
        self,
        email: str | None = None,
        password: str | None = None,
        active: bool | None = None,
        admin: bool | None = None,
        user_id: UUID | None = None,
    ) -> None:
        """
        Atualiza os dados do usuário e emite evento de atualização.

        Args:
            email: Novo email (opcional).
            password: Nova senha (opcional).
            active: Novo status de ativação (opcional).
            admin: Novo status de administrador (opcional).
            user_id: ID do usuário que está realizando a atualização (opcional).
        """
        self._operation_type = OperationType.UPDATE
        self._set_update_audit(user_id)

        old_data: dict = {}
        new_data: dict = {}

        self._track_change(old_data, new_data, "email", email)
        self._track_change(old_data, new_data, "active", active)
        self._track_change(old_data, new_data, "admin", admin)

        if password is not None:
            new_data["password"] = AuditConstant.REDACTED_PASSWORD
            self._password_hash = self.encrypt_password(password)

        self.add_event(
            UserUpdated(
                id=self.id,
                company=self.company,
                entity_type=EntityType.USER,
                old_data=old_data,
                new_data=new_data,
            )
        )

    def delete(self, user_id: UUID | None = None) -> None:
        """Marca o agregado como deletado (soft delete) e emite evento de exclusão."""
        self._operation_type = OperationType.DELETE

        old_data = {
            "email": self.email,
            "cpf": self.cpf,
            "active": self.active,
            "admin": self.admin,
        }

        self._set_delete_audit(user_id)

        self.add_event(
            UserDeleted(
                id=self.id,
                company=self.company,
                entity_type=EntityType.USER,
                old_data=old_data,
            )
        )


@dataclass(kw_only=True)
class PublicUser(Aggregate, UserSecurity):
    """Agregado que representa um usuário público (dados criptografados) no domínio."""

    id: UUID
    company: UUID
    email_encrypted: bytes
    email_hash: str

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create_registration_aggregate(
        cls,
        user: User,
    ) -> "PublicUser":
        """
        Cria um agregado PublicUser a partir de um usuário privado para cadastro.

        Args:
            user: Agregado User de origem.

        Returns:
            Nova instância de PublicUser com email criptografado e hash.
        """
        encrypted_email = cls.encrypt_email(user.email)
        email_hash = cls.hash_email(user.email)

        return PublicUser(
            id=user.id,
            company=user.company,
            email_encrypted=encrypted_email,
            email_hash=email_hash,
            _password_hash=user.password_hash,
            active=user.active,
        )

    def register(self) -> None:
        """Marca o agregado para inserção no banco de dados."""
        self._operation_type = OperationType.INSERT

    def update(self, email: str, password: str, active: bool) -> None:
        """
        Atualiza os dados do usuário público.

        Args:
            email: Novo email (será criptografado e hasheado).
            password: Novo hash da senha.
            active: Novo status de ativação.
        """
        self._operation_type = OperationType.UPDATE

        self.email_encrypted = self.encrypt_email(email)
        self.email_hash = self.hash_email(email)
        self._password_hash = password
        self.active = active

    def remove(self) -> None:
        """Marca o agregado como deletado (soft delete)."""
        self._operation_type = OperationType.DELETE
        self._set_delete_audit(user_id=None)
