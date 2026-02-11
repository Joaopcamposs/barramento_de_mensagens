"""Módulo de views de consulta de Company."""

from messagebus.domains import Domain
from business_contexts.adapters.repository.view_repo.company import (
    CompanyViewRepo,
)
from business_contexts.domain.entitites.company import Company
from messagebus.unity_of_work import UnitOfWork


async def view_company(
    uow: UnitOfWork,
    name: str | None = None,
    include_deleted: bool = False,
) -> list[Company]:
    """
    Consulta empresas. Se o nome for informado, filtra pelo nome.
    Caso contrário, retorna todas as empresas.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        name: Nome da empresa (opcional). Se None, retorna todas.
        include_deleted: Se True, inclui empresas deletadas.

    Returns:
        Lista de entidades Company.
    """
    async with uow(Domain.company) as uow:
        view_repo: CompanyViewRepo = uow.view_repo
        if name:
            company = await view_repo.get_by_name(name, include_deleted=include_deleted)
            if not company:
                return []
            return [company]

        companies = await view_repo.get_all(include_deleted=include_deleted)
        return companies
