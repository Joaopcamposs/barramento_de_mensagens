"""Módulo de views de consulta de Company."""

from messagebus.domains import Domain
from business_contexts.adapters.repository.view_repo.company import (
    CompanyViewRepo,
)
from business_contexts.domain.entitites.company import Company
from messagebus.unity_of_work import UnitOfWork


async def view_company(uow: UnitOfWork, name: str | None = None) -> list[Company]:
    """
    Consulta empresas. Se o nome for informado, filtra pelo nome.
    Caso contrário, retorna todas as empresas.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        name: Nome da empresa (opcional). Se None, retorna todas.

    Returns:
        Lista de entidades Company.
    """
    async with uow(Domain.company) as uow:
        view_repo: CompanyViewRepo = uow.view_repo
        if name:
            company = await view_repo.get_by_name(name)
            if not company:
                return []
            return [company]

        companies = await view_repo.get_all()
        return companies
