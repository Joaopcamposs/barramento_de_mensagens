"""Módulo do repositório de domínio de User."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import select

from business_contexts.adapters.repository.mixins.public_user import PublicUserMixin
from business_contexts.adapters.repository.mixins.upsert import UpsertMixin
from business_contexts.domain.aggregate.user import User
from business_contexts.domain.excecoes import (
    UserAlreadyRegistered,
    UserNotFound,
)
from messagebus.entities import DomainRepository


class AbstractUserDomainRepo(DomainRepository):
    """Repositório abstrato de domínio para User."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Inicializa o repositório e o conjunto de agregados rastreados."""
        super().__init__(*args, **kwargs)
        self.seen: set[User] = set()

    async def add(self, user: User) -> None:
        """
        Adiciona um usuário ao repositório e à lista de rastreados.

        Args:
            user: Agregado User a ser adicionado.
        """
        self.seen.add(user)
        await self._add(user)

    @abstractmethod
    async def _add(self, user: User) -> None:
        """Implementação interna de adição."""
        raise NotImplementedError

    async def remove(self, user: User) -> None:
        """
        Remove um usuário do repositório.

        Args:
            user: Agregado User a ser removido.
        """
        self.seen.add(user)
        await self._remove(user)

    @abstractmethod
    async def _remove(self, user: User) -> None:
        """Implementação interna de remoção."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> User:
        """
        Busca um usuário pelo email.

        Args:
            email: Email do usuário.

        Returns:
            Agregado User encontrado.
        """
        raise NotImplementedError()


class UserDomainRepo(AbstractUserDomainRepo, PublicUserMixin, UpsertMixin):
    """Implementação concreta do repositório de domínio de User."""

    async def create_aggregate(
        self,
        company: UUID,
        email: str,
        cpf: str,
        password: str,
        active: bool = True,
        admin: bool = False,
    ) -> User:
        """
        Cria um novo agregado User, verificando duplicidade de email.

        Args:
            company: ID da empresa associada.
            email: Email do usuário.
            cpf: CPF do usuário.
            password: Senha do usuário.
            active: Se o usuário está ativo.
            admin: Se o usuário é administrador.

        Returns:
            Nova instância do agregado User.

        Raises:
            UserAlreadyRegistered: Se já existe usuário com o mesmo email.
        """
        async with self.session as session:
            existing_user = (
                await session.execute(
                    select(User).where(
                        User.email == email,
                        User.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if existing_user:
                raise UserAlreadyRegistered

        return User.create_aggregate(
            company=company,
            email=email,
            cpf=cpf,
            password=password,
            active=active,
            admin=admin,
        )

    async def get_by_email(self, email: str) -> User:
        """
        Busca um usuário pelo email.

        Args:
            email: Email do usuário.

        Returns:
            Agregado User encontrado.

        Raises:
            UserNotFound: Se o usuário não for encontrado.
        """
        async with self.session as session:
            user = (
                await session.execute(
                    select(User).where(
                        User.email == email,
                        User.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not user:
                raise UserNotFound

            aggregate = User(
                id=user.id,
                company=user.company,
                email=user.email,
                cpf=user.cpf,
                _password_hash=user.password_hash,
                active=user.active,
                admin=user.admin,
                created_at=user.created_at,
                created_by=user.created_by,
                updated_at=user.updated_at,
                updated_by=user.updated_by,
                deleted_at=user.deleted_at,
                deleted_by=user.deleted_by,
            )

        return aggregate

    async def get_by_id(self, id: UUID) -> User:
        """
        Busca um usuário pelo ID.

        Args:
            id: UUID do usuário.

        Returns:
            Agregado User encontrado.

        Raises:
            UserNotFound: Se o usuário não for encontrado.
        """
        async with self.session as session:
            user = (
                await session.execute(
                    select(User).where(
                        User.id == id,
                        User.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not user:
                raise UserNotFound

            aggregate = User(
                id=user.id,
                company=user.company,
                email=user.email,
                cpf=user.cpf,
                _password_hash=user.password_hash,
                active=user.active,
                admin=user.admin,
                created_at=user.created_at,
                created_by=user.created_by,
                updated_at=user.updated_at,
                updated_by=user.updated_by,
                deleted_at=user.deleted_at,
                deleted_by=user.deleted_by,
            )

        return aggregate

    async def _add(self, user: User) -> None:
        """Persiste um usuário no banco de dados (inserção ou atualização)."""
        data = {
            "id": user.id,
            "company": user.company,
            "email": user.email,
            "cpf": user.cpf,
            "_password_hash": user.password_hash,
            "active": user.active,
            "admin": user.admin,
            "created_at": user.created_at,
            "created_by": user.created_by,
            "updated_at": user.updated_at,
            "updated_by": user.updated_by,
            "deleted_at": user.deleted_at,
            "deleted_by": user.deleted_by,
        }
        await self._execute_upsert(User, user, data)

    async def _remove(self, user: User) -> None:
        """Marca um usuário como deletado no banco de dados (soft delete)."""
        await self._execute_soft_delete(User, user)
