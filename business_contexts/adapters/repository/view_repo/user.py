"""Módulo do repositório de consulta de User."""

from sqlalchemy import select

from messagebus.entities import ViewRepository
from business_contexts.domain.aggregate.user import User as UserAggregate
from business_contexts.domain.entitites.user import User


class UserViewRepo(ViewRepository):
    """Repositório de consulta para User."""

    async def get_by_email(
        self, email: str, include_deleted: bool = False
    ) -> User | None:
        """
        Busca um usuário pelo email (somente leitura).

        Args:
            email: Email do usuário.
            include_deleted: Se True, inclui usuários deletados.

        Returns:
            Entidade User ou None se não encontrado.
        """
        async with self.session as session:
            query = select(UserAggregate).where(UserAggregate.email == email)
            if not include_deleted:
                query = query.where(UserAggregate.deleted == False)

            user = (await session.execute(query)).scalar_one_or_none()
            if not user:
                return None

            entity = User(
                id=user.id,
                company=user.company,
                email=user.email,
                deleted=user.deleted,
            )

        return entity

    async def get_all(self, include_deleted: bool = False) -> list[User]:
        """
        Busca todos os usuários (somente leitura).

        Args:
            include_deleted: Se True, inclui usuários deletados.

        Returns:
            Lista de entidades User.
        """
        async with self.session as session:
            query = select(UserAggregate)
            if not include_deleted:
                query = query.where(UserAggregate.deleted == False)

            users = (await session.execute(query)).scalars()
            if not users:
                return []

            return [
                User(
                    id=user.id,
                    company=user.company,
                    email=user.email,
                    deleted=user.deleted,
                )
                for user in users
            ]
