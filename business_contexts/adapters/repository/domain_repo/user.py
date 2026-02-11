"""Módulo do repositório de domínio de User."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import select, update, insert, delete
from sqlalchemy.sql import Executable

from messagebus.entities import DomainRepository, OperationType
from business_contexts.domain.aggregate.user import User
from business_contexts.domain.excecoes import (
    UserAlreadyRegistered,
    UserNotFound,
)


class AbstractUserDomainRepo(DomainRepository):
    """Repositório abstrato de domínio para User."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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


class UserDomainRepo(AbstractUserDomainRepo):
    """Implementação concreta do repositório de domínio de User."""

    async def create_aggregate(
        self,
        company: UUID,
        email: str,
        password: str,
    ) -> User:
        """
        Cria um novo agregado User, verificando duplicidade de email.

        Args:
            company: ID da empresa associada.
            email: Email do usuário.
            password: Senha do usuário.

        Returns:
            Nova instância do agregado User.

        Raises:
            UserAlreadyRegistered: Se já existe usuário com o mesmo email.
        """
        async with self.session as session:
            existing_user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing_user:
                raise UserAlreadyRegistered

        return User.create_aggregate(
            company=company,
            email=email,
            password=password,
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
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if not user:
                raise UserNotFound

            aggregate = User(
                id=user.id,
                company=user.company,
                email=user.email,
                password=user.password,
            )

        return aggregate

    async def _add(
        self,
        user: User,
    ) -> None:
        """Persiste um usuário no banco de dados (inserção ou atualização)."""
        data = {
            "id": user.id,
            "company": user.company,
            "email": user.email,
            "password": user.password,
        }

        operation: Executable
        match user._operation_type:
            case OperationType.INSERT:
                operation = insert(User).values(data)
            case OperationType.UPDATE:
                operation = update(User).where(User.id == user.id).values(data)
            case _:
                raise ValueError("Unsupported operation type for domain repository.")

        await self.session.execute(operation)

    async def _remove(self, user: User) -> None:
        """Remove um usuário do banco de dados."""
        operation = delete(User).where(User.id == user.id)

        await self.session.execute(operation)
