"""Módulo do repositório de consulta de User."""

from uuid import UUID

from sqlalchemy import select

from messagebus.entities import ViewRepository
from business_contexts.domain.aggregate.user import User as UserAggregate
from business_contexts.domain.entitites.user import User


class UserViewRepo(ViewRepository):
    """Repositório de consulta para User."""

    async def get_by_email(
        self, company: UUID, email: str, include_deleted: bool = False
    ) -> User | None:
        """
        Busca um usuário pelo email dentro de uma empresa (somente leitura).

        Args:
            company: ID da empresa. Obrigatório para filtrar usuários.
            email: Email do usuário.
            include_deleted: Se True, inclui usuários deletados.

        Returns:
            Entidade User ou None se não encontrado.
        """
        async with self.session as session:
            query = select(UserAggregate).where(
                UserAggregate.company == company,
                UserAggregate.email == email,
            )
            if not include_deleted:
                query = query.where(
                    UserAggregate.deleted == False  # noqa: E712
                )

            user = (await session.execute(query)).scalar_one_or_none()
            if not user:
                return None

            entity = User(
                id=user.id,
                company=user.company,
                email=user.email,
                cpf=user.cpf,
                active=user.active,
                admin=user.admin,
                deleted=user.deleted,
            )

        return entity

    async def get_all(self, company: UUID, include_deleted: bool = False) -> list[User]:
        """
        Busca todos os usuários de uma empresa (somente leitura).

        Args:
            company: ID da empresa. Obrigatório para filtrar usuários.
            include_deleted: Se True, inclui usuários deletados.

        Returns:
            Lista de entidades User da empresa informada.
        """
        async with self.session as session:
            query = select(UserAggregate).where(
                UserAggregate.company == company,
            )
            if not include_deleted:
                query = query.where(
                    UserAggregate.deleted == False  # noqa: E712
                )

            users = (await session.execute(query)).scalars()
            if not users:
                return []

            return [
                User(
                    id=user.id,
                    company=user.company,
                    email=user.email,
                    cpf=user.cpf,
                    active=user.active,
                    admin=user.admin,
                    deleted=user.deleted,
                )
                for user in users
            ]
