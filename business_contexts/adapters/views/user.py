"""Módulo de views de consulta de User."""

from uuid import UUID

from messagebus.domains import Domain
from business_contexts.adapters.repository.view_repo.user import (
    UserViewRepo,
)
from business_contexts.domain.entitites.user import User
from messagebus.unity_of_work import UnitOfWork


async def view_user(
    uow: UnitOfWork,
    company: UUID,
    email: str | None = None,
    include_deleted: bool = False,
) -> list[User]:
    """
    Consulta usuários de uma empresa. Se o email for informado, filtra pelo email.
    Caso contrário, retorna todos os usuários da empresa.

    A empresa é obrigatória e somente os usuários da empresa informada
    são retornados.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        company: ID da empresa. Obrigatório.
        email: Email do usuário (opcional). Se None, retorna todos da empresa.
        include_deleted: Se True, inclui usuários deletados.

    Returns:
        Lista de entidades User da empresa informada.
    """
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = uow.view_repo
        if email:
            user = await view_repo.get_by_email(
                company=company, email=email, include_deleted=include_deleted
            )
            if not user:
                return []
            return [user]

        users = await view_repo.get_all(
            company=company, include_deleted=include_deleted
        )
        return users
