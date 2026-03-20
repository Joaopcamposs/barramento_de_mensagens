"""Módulo de endpoints da API para Company."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

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
from business_contexts.services.handlers.security import get_current_user
from business_contexts.bootstrap import bootstrap_apis
from messagebus.messagebus import MessageBus

router = APIRouter(
    prefix="/v1", tags=["Companies"], dependencies=[Depends(get_current_user)]
)


@router.post("/company", response_model=UUID, status_code=status.HTTP_201_CREATED)
async def post_company(
    body: CreateCompanySchema, bus: MessageBus = Depends(bootstrap_apis)
) -> UUID:
    """Cria uma nova empresa."""

    command = CreateCompany(
        legal_name=body.legal_name,
        trade_name=body.trade_name,
        responsible_name=body.responsible_name,
        email=body.email,
        cpf=body.cpf,
        cnpj=body.cnpj,
        password=body.password,
        active=body.active,
    )
    company_id: UUID = await bus.handle(command)
    return company_id


@router.put("/company", status_code=status.HTTP_200_OK)
async def put_company(
    legal_name: str, body: UpdateCompanySchema, bus: MessageBus = Depends(bootstrap_apis)
) -> None:
    """Atualiza uma empresa existente."""

    command = UpdateCompany(
        legal_name=legal_name,
        new_legal_name=body.new_legal_name,
        new_trade_name=body.new_trade_name,
        new_responsible_name=body.new_responsible_name,
        new_email=body.new_email,
        new_active=body.new_active,
    )
    await bus.handle(command)


@router.get("/company", response_model=list[ReadCompanySchema])
async def get_company(
    legal_name: str | None = None,
    include_deleted: bool = False,
    bus: MessageBus = Depends(bootstrap_apis),
):
    """Consulta empresas. Se a razão social for informada, filtra pela razão social."""
    companies = await view_company(
        bus.uow, legal_name=legal_name, include_deleted=include_deleted
    )
    return companies


@router.delete("/company", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    legal_name: str, bus: MessageBus = Depends(bootstrap_apis)
) -> None:
    """Exclui uma empresa pela razão social."""

    command = DeleteCompany(legal_name=legal_name)
    await bus.handle(command)
