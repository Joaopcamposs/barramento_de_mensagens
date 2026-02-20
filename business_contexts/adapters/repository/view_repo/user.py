"""Módulo do repositório de consulta de User."""

from uuid import UUID

from sqlalchemy import select

from business_contexts.domain.aggregate.user import PublicUser as PublicUserAggregate
from business_contexts.domain.aggregate.user import User as UserAggregate
from business_contexts.domain.entitites.user import PublicUser, User
from messagebus.entities import ViewRepository


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
            query = select(UserAggregate).where(
                UserAggregate.email == email,
            )
            if not include_deleted:
                query = query.where(UserAggregate.deleted_at.is_(None))

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
                created_at=user.created_at,
                created_by=user.created_by,
                updated_at=user.updated_at,
                updated_by=user.updated_by,
                deleted_at=user.deleted_at,
                deleted_by=user.deleted_by,
            )

        return entity

    async def get_by_id(self, id: UUID) -> User | None:
        """
        Busca um usuário pelo ID (somente leitura).

        Args:
            id: UUID do usuário.

        Returns:
            Entidade User ou None se não encontrado.
        """
        async with self.session as session:
            query = select(UserAggregate).where(
                UserAggregate.id == id,
                UserAggregate.deleted_at.is_(None),
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
                _password_hash=user.password_hash,
                created_at=user.created_at,
                created_by=user.created_by,
                updated_at=user.updated_at,
                updated_by=user.updated_by,
                deleted_at=user.deleted_at,
                deleted_by=user.deleted_by,
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
            query = select(UserAggregate).where()
            if not include_deleted:
                query = query.where(UserAggregate.deleted_at.is_(None))

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
                    created_at=user.created_at,
                    created_by=user.created_by,
                    updated_at=user.updated_at,
                    updated_by=user.updated_by,
                    deleted_at=user.deleted_at,
                    deleted_by=user.deleted_by,
                )
                for user in users
            ]

    async def get_public_user_by_email(self, email: str) -> PublicUser | None:
        """
        Busca um usuário público pelo email (somente leitura).

        Args:
            email: Email do usuário (será convertido em hash para busca).

        Returns:
            Entidade PublicUser ou None se não encontrado.
        """
        email_hash = PublicUser.hash_email(email)
        async with self.session as session:
            result = (
                await session.execute(
                    select(PublicUserAggregate).where(
                        PublicUserAggregate.email_hash == email_hash,
                        PublicUserAggregate.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not result:
                return None

            public_user_entity = PublicUser(
                id=result.id,
                company=result.company,
                active=result.active,
                email_encrypted=result.email_encrypted,
                email_hash=result.email_hash,
                _password_hash=result.password_hash,
            )
            return public_user_entity
