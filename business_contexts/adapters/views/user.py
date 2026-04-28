"""Módulo de views de consulta de User."""

from typing import cast
from uuid import UUID

from business_contexts.adapters.repository.view_repo.user import (
    UserViewRepo,
)
from business_contexts.domain.entitites.user import PublicUser, User
from business_contexts.domain.excecoes import UserNotFound
from business_contexts.domains import Domain
from messagebus.unity_of_work import UnitOfWork


async def get_public_user_by_email(email: str) -> PublicUser:
    """
    Busca um usuário público pelo email.

    Args:
        email: Email do usuário.

    Returns:
        Entidade PublicUser.

    Raises:
        UserNotFound: Se o usuário público não existir.
    """
    uow = UnitOfWork(schema="public", read_only=True)
    async with uow(Domain.user) as uow:
        view_repo = uow.get_view_repo(UserViewRepo)

        user = await view_repo.get_public_user_by_email(email)
        if not user:
            raise UserNotFound

    return user


async def view_user(
    uow: UnitOfWork,
    email: str | None = None,
    include_deleted: bool = False,
) -> list[User]:
    """
    Consulta usuários de uma empresa. Se o email for informado, filtra pelo email.
    Caso contrário, retorna todos os usuários da empresa.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        email: Email do usuário (opcional). Se None, retorna todos da empresa.
        include_deleted: Se True, inclui usuários deletados.

    Returns:
        Lista de entidades User da empresa informada.
    """
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = cast(UserViewRepo, uow.view_repo)
        if email:
            user = await view_repo.get_by_email(
                email=email, include_deleted=include_deleted
            )
            if not user:
                return []
            return [user]

        users = await view_repo.get_all(include_deleted=include_deleted)
        return users


async def get_tenant_user(schema: str | UUID, user_id: UUID) -> User:
    """Carrega o usuário autenticado com o estado mais recente do tenant."""
    uow = UnitOfWork(schema=str(schema), read_only=True)
    async with uow(Domain.user) as user_uow:
        user_view_repo = user_uow.get_view_repo(UserViewRepo)
        current_user = await user_view_repo.get_by_id(user_id)
        if current_user is None:
            raise UserNotFound()
        return current_user
