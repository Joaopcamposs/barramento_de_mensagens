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
    bus = bootstrap()

    command = CreateUser(
        company=body.company,
        email=body.email,
        password=body.password,
    )
    user_id: UUID = await bus.handle(command)
    return user_id


@router.put("/user", status_code=status.HTTP_200_OK)
async def put_user(body: UpdateUserSchema) -> None:
    """Atualiza um usuário existente."""
    bus = bootstrap()

    command = UpdateUser(
        email=body.email,
        new_email=body.new_email,
        new_password=body.new_password,
    )
    await bus.handle(command)


@router.get("/user", response_model=list[ReadUserSchema])
async def get_user(email: str | None = None, include_deleted: bool = False):
    """Consulta usuários. Se o email for informado, filtra pelo email."""
    uow = UnitOfWork()
    user = await view_user(uow, email, include_deleted=include_deleted)
    return user


@router.delete("/user", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(email: str) -> None:
    """Exclui um usuário pelo email."""
    bus = bootstrap()

    command = DeleteUser(email=email)
    await bus.handle(command)
