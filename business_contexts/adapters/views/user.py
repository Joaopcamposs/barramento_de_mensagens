"""Módulo de views de consulta de User."""

from messagebus.domains import Domain
from business_contexts.adapters.repository.view_repo.user import (
    UserViewRepo,
)
from business_contexts.domain.entitites.user import User
from messagebus.unity_of_work import UnitOfWork


async def view_user(uow: UnitOfWork, email: str | None = None) -> list[User]:
    """
    Consulta usuários. Se o email for informado, filtra pelo email.
    Caso contrário, retorna todos os usuários.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        email: Email do usuário (opcional). Se None, retorna todos.

    Returns:
        Lista de entidades User.
    """
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = uow.view_repo
        if email:
            user = await view_repo.get_by_email(email)
            if not user:
                return []
            return [user]

        user = await view_repo.get_all()
        return user
