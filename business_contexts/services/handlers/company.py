"""Módulo de handlers de comandos e eventos do domínio Company."""

from uuid import UUID

from messagebus.messagebus import logger
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.repository.domain_repo.company import (
    CompanyDomainRepo,
)
from business_contexts.domain.commands.company import (
    CreateCompany,
    UpdateCompany,
    DeleteCompany,
)
from messagebus.domains import Domain
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyUpdated,
    CompanyDeleted,
)


async def create_company(command: CreateCompany, uow: UnitOfWork) -> UUID:
    """Handler para criação de empresa."""
    async with uow(Domain.company) as uow:
        domain_repo: CompanyDomainRepo = uow.domain_repo

        company = await domain_repo.create_aggregate(
            name=command.name,
        )
        company.create()

        await domain_repo.add(company)
        await uow.commit()

        return company.id


async def update_company(command: UpdateCompany, uow: UnitOfWork) -> None:
    """Handler para atualização de empresa."""
    async with uow(Domain.company) as uow:
        domain_repo: CompanyDomainRepo = uow.domain_repo

        company = await domain_repo.get_by_name(
            name=command.name,
        )
        company.update(new_name=command.new_name)

        await domain_repo.add(company)
        await uow.commit()


async def delete_company(command: DeleteCompany, uow: UnitOfWork) -> None:
    """Handler para exclusão de empresa."""
    async with uow(Domain.company) as uow:
        domain_repo: CompanyDomainRepo = uow.domain_repo

        company = await domain_repo.get_by_name(
            name=command.name,
        )
        company.delete()

        await domain_repo.remove(company)
        await uow.commit()


async def company_created(event: CompanyCreated, uow: UnitOfWork) -> None:
    """Handler para o evento de empresa criada."""
    logger.info(f"Event CompanyCreated for company: {event.id} received")


async def company_updated(event: CompanyUpdated, uow: UnitOfWork) -> None:
    """Handler para o evento de empresa atualizada."""
    logger.info(f"Event CompanyUpdated for company: {event.id} received")


async def company_deleted(event: CompanyDeleted, uow: UnitOfWork) -> None:
    """Handler para o evento de empresa excluída."""
    logger.info(f"Event CompanyDeleted for company {event.id} received")
