"""Módulo mixin para operações de repositório do usuário público."""

from abc import ABC
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from business_contexts.domain.aggregate.user import PublicUser
from messagebus.entities import OperationType


class PublicUserMixin(ABC):
    """Mixin com operações de repositório para o agregado PublicUser."""

    session: AsyncSession

    async def get_public_user_by_id(self, id: UUID) -> PublicUser | None:
        """
        Busca um usuário público pelo ID.

        Args:
            id: UUID do usuário público.

        Returns:
            Agregado PublicUser ou None se não encontrado.
        """
        async with self.session as session:
            result = (
                await session.execute(
                    select(PublicUser).where(
                        PublicUser.id == id,
                        PublicUser.deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if not result:
                return None

            public_user = PublicUser(
                id=result.id,
                company=result.company,
                active=result.active,
                email_encrypted=result.email_encrypted,
                email_hash=result.email_hash,
                _password_hash=result.password_hash,
            )
            return public_user

    async def add_public_user(
        self,
        public_user: PublicUser,
    ) -> None:
        """
        Persiste um usuário público no banco de dados (inserção ou atualização).

        Args:
            public_user: Agregado PublicUser a ser persistido.

        Raises:
            ValueError: Se o tipo de operação não for suportado.
        """
        data = {
            "id": public_user.id,
            "company": public_user.company,
            "active": public_user.active,
            "email_encrypted": public_user.email_encrypted,
            "email_hash": public_user.email_hash,
            "_password_hash": public_user.password_hash,
            "deleted": public_user.deleted,
        }

        match public_user.operation_type:
            case OperationType.INSERT:
                operation = insert(PublicUser).values(data)
            case OperationType.UPDATE:
                operation = (
                    update(PublicUser).where(PublicUser.id == public_user.id).values(data)
                )
            case _:
                raise ValueError("Unsupported operation type for domain repository.")

        await self.session.execute(operation)

    async def remove_public_user(self, public_user: PublicUser) -> None:
        """
        Marca um usuário público como deletado no banco de dados (soft delete).

        Args:
            public_user: Agregado PublicUser a ser removido.
        """
        operation = (
            update(PublicUser)
            .where(PublicUser.id == public_user.id)
            .values({"deleted": True})
        )
        await self.session.execute(operation)
