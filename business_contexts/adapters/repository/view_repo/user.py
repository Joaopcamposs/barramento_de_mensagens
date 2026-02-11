"""Módulo do repositório de consulta de User."""

from sqlalchemy import select

from messagebus.entities import ViewRepository
from business_contexts.domain.aggregate.user import User as UserAggregate
from business_contexts.domain.entitites.user import User


class UserViewRepo(ViewRepository):
    """Repositório de consulta para User."""

    async def get_by_email(self, email: str) -> User | None:
        """
        Busca um usuário pelo email (somente leitura).

        Args:
            email: Email do usuário.

        Returns:
            Entidade User ou None se não encontrado.
        """
        async with self.session as session:
            user = (
                await session.execute(
                    select(UserAggregate).where(
                        UserAggregate.email == email,
                    )
                )
            ).scalar_one_or_none()
            if not user:
                return None

            entity = User(
                id=user.id,
                company=user.company,
                email=user.email,
            )

        return entity

    async def get_all(self) -> list[User]:
        """
        Busca todos os usuários (somente leitura).

        Returns:
            Lista de entidades User.
        """
        async with self.session as session:
            users = (await session.execute(select(UserAggregate))).scalars()
            if not users:
                return []

            return [
                User(
                    id=user.id,
                    company=user.company,
                    email=user.email,
                )
                for user in users
            ]
