"""Módulo de views de consulta de Company."""

from typing import cast

from business_contexts.adapters.repository.view_repo.company import (
    CompanyViewRepo,
)
from business_contexts.domain.entitites.company import Company
from messagebus.domains import Domain
from messagebus.unity_of_work import UnitOfWork


async def view_company(
    uow: UnitOfWork,
    legal_name: str | None = None,
    include_deleted: bool = False,
) -> list[Company]:
    """
    Consulta empresas. Se a razão social for informada, filtra pela razão social.
    Caso contrário, retorna todas as empresas.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        legal_name: Razão social da empresa (opcional). Se None, retorna todas.
        include_deleted: Se True, inclui empresas deletadas.

    Returns:
        Lista de entidades Company.
    """
    async with uow(Domain.company) as uow:
        view_repo: CompanyViewRepo = cast(CompanyViewRepo, uow.view_repo)
        if legal_name:
            company = await view_repo.get_by_legal_name(
                legal_name, include_deleted=include_deleted
            )
            if not company:
                return []
            return [company]

        companies = await view_repo.get_all(include_deleted=include_deleted)
        return companies
