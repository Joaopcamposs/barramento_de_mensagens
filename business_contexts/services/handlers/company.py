"""Módulo de handlers de comandos e eventos do domínio Company."""

from uuid import UUID

from business_contexts.adapters.repository.domain_repo.company import (
    CompanyDomainRepo,
)
from business_contexts.domain.commands.company import (
    CreateCompany,
    DeleteCompany,
    UpdateCompany,
)
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyDeleted,
    CompanyUpdated,
)
from infra.database import delete_schema
from messagebus.domains import Domain
from messagebus.messagebus import logger
from messagebus.unity_of_work import UnitOfWork


async def create_company(command: CreateCompany, uow: UnitOfWork) -> UUID:
    """Handler para criação de empresa."""
    try:
        async with uow(Domain.company) as uow:
            domain_repo: CompanyDomainRepo = uow.domain_repo

            company = await domain_repo.create_aggregate(
                legal_name=command.legal_name,
                trade_name=command.trade_name,
                responsible_name=command.responsible_name,
                email=command.email,
                cpf=command.cpf,
                cnpj=command.cnpj,
                active=command.active,
                _first_company_id=command._first_company_id,
            )
            company.create(
                user_id=uow.user.id if uow.user else None,
                password=command.password,
                should_create_user=command.should_create_user,
            )

            await domain_repo.add(company)
            await uow.commit()

            return company.id
    except Exception as error:
        await delete_schema(str(command.legal_name))
        logger.error(f"Erro ao criar empresa. O schema foi dropado: {error}")
        raise error


async def update_company(command: UpdateCompany, uow: UnitOfWork) -> None:
    """Handler para atualização de empresa."""
    async with uow(Domain.company) as uow:
        domain_repo: CompanyDomainRepo = uow.domain_repo

        company = await domain_repo.get_by_legal_name(
            legal_name=command.legal_name,
        )
        company.update(
            legal_name=command.new_legal_name,
            trade_name=command.new_trade_name,
            responsible_name=command.new_responsible_name,
            email=command.new_email,
            active=command.new_active,
        )

        await domain_repo.add(company)
        await uow.commit()


async def delete_company(command: DeleteCompany, uow: UnitOfWork) -> None:
    """Handler para exclusão (soft delete) de empresa."""
    async with uow(Domain.company) as uow:
        domain_repo: CompanyDomainRepo = uow.domain_repo

        company = await domain_repo.get_by_legal_name(
            legal_name=command.legal_name,
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
