"""Módulo de endpoints da API para Company."""

from uuid import UUID

from fastapi import APIRouter, status

from messagebus.bootstrap import bootstrap
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.views.company import view_company
from business_contexts.domain.commands.company import (
    CreateCompany,
    DeleteCompany,
    UpdateCompany,
)
from business_contexts.entrypoints.schemas.company import (
    CreateCompanySchema,
    ReadCompanySchema,
    UpdateCompanySchema,
)

router = APIRouter(prefix="/v1", tags=["Companies"])


@router.post("/company", response_model=UUID, status_code=status.HTTP_201_CREATED)
async def post_company(body: CreateCompanySchema) -> UUID:
    """Cria uma nova empresa."""
    bus = bootstrap()

    command = CreateCompany(name=body.name)
    company_id: UUID = await bus.handle(command)
    return company_id


@router.put("/company", status_code=status.HTTP_200_OK)
async def put_company(body: UpdateCompanySchema) -> None:
    """Atualiza uma empresa existente."""
    bus = bootstrap()

    command = UpdateCompany(name=body.name, new_name=body.new_name)
    await bus.handle(command)


@router.get("/company", response_model=list[ReadCompanySchema])
async def get_company(name: str | None = None):
    """Consulta empresas. Se o nome for informado, filtra pelo nome."""
    uow = UnitOfWork()
    companies = await view_company(uow, name)
    return companies


@router.delete("/company", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(name: str) -> None:
    """Exclui uma empresa pelo nome."""
    bus = bootstrap()

    command = DeleteCompany(name=name)
    await bus.handle(command)
