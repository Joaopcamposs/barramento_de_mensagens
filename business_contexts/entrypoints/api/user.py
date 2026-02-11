"""Módulo de endpoints da API para User."""

from uuid import UUID

from fastapi import APIRouter, status

from messagebus.bootstrap import bootstrap
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.views.user import view_user
from business_contexts.domain.commands.user import (
    CreateUser,
    DeleteUser,
    UpdateUser,
)
from business_contexts.entrypoints.schemas.user import (
    CreateUserSchema,
    ReadUserSchema,
    UpdateUserSchema,
)

router = APIRouter(prefix="/v1", tags=["Users"])


@router.post("/user", response_model=UUID, status_code=status.HTTP_201_CREATED)
async def post_user(body: CreateUserSchema) -> UUID:
    """Cria um novo usuário."""
    bus = bootstrap(schema=str(body.company))

    command = CreateUser(
        company=body.company,
        email=body.email,
        cpf=body.cpf,
        password=body.password,
        active=body.active,
        admin=body.admin,
    )
    user_id: UUID = await bus.handle(command)
    return user_id


@router.put("/user", status_code=status.HTTP_200_OK)
async def put_user(body: UpdateUserSchema) -> None:
    """Atualiza um usuário existente."""
    bus = bootstrap(schema=str(body.company))

    command = UpdateUser(
        email=body.email,
        new_email=body.new_email,
        new_password=body.new_password,
        new_active=body.new_active,
        new_admin=body.new_admin,
    )
    await bus.handle(command)


@router.get("/user", response_model=list[ReadUserSchema])
async def get_user(
    company: UUID,
    email: str | None = None,
    include_deleted: bool = False,
):
    """Consulta usuários de uma empresa. A empresa é obrigatória."""
    uow = UnitOfWork(schema=str(company))
    users = await view_user(
        uow, company=company, email=email, include_deleted=include_deleted
    )
    return users


@router.delete("/user", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(company: str, email: str) -> None:
    """Exclui um usuário pelo email."""
    bus = bootstrap(schema=str(company))

    command = DeleteUser(email=email)
    await bus.handle(command)
