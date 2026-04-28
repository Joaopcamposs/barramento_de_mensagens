"""Módulo mixin para operações de repositório do usuário público."""

from abc import ABC
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from business_contexts.domain.aggregate.user import PublicUser


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
        result = (
            await self.session.execute(
                select(PublicUser).where(
                    PublicUser.id == id,
                )
            )
        ).scalar_one_or_none()
        if not result:
            return None
        return result

    async def add_public_user(self, public_user: PublicUser) -> None:
        """
        Persiste um usuário público no banco de dados (inserção).

        Args:
            public_user: Agregado PublicUser a ser persistido.
        """
        data = {
            "id": public_user.id,
            "company": public_user.company,
            "email_encrypted": public_user.email_encrypted,
            "email_lookup_hmac": public_user.email_lookup_hmac,
            "cpf_lookup_hmac": public_user.cpf_lookup_hmac,
        }
        operation = insert(PublicUser).values(data)
        await self.session.execute(operation)

    async def update_public_user_cpf(self, public_user: PublicUser) -> None:
        """Atualiza apenas o HMAC de lookup do CPF no usuário público."""
        operation = (
            update(PublicUser)
            .where(PublicUser.id == public_user.id)
            .values({"cpf_lookup_hmac": public_user.cpf_lookup_hmac})
        )
        await self.session.execute(operation)

    async def remove_public_user(self, public_user: PublicUser) -> None:
        """
        Remove um usuário público do banco de dados.

        Args:
            public_user: Agregado PublicUser a ser removido.
        """
        operation = delete(PublicUser).where(PublicUser.id == public_user.id)
        await self.session.execute(operation)
