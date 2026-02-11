"""Módulo de handlers de comandos e eventos do domínio User."""

from uuid import UUID

from messagebus.messagebus import logger
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.repository.domain_repo.user import (
    UserDomainRepo,
)
from business_contexts.domain.commands.user import (
    CreateUser,
    UpdateUser,
    DeleteUser,
)
from messagebus.domains import Domain
from business_contexts.domain.events.user import (
    UserCreated,
    UserUpdated,
    UserDeleted,
)


async def create_user(command: CreateUser, uow: UnitOfWork) -> UUID:
    """Handler para criação de usuário."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = uow.domain_repo

        user = await domain_repo.create_aggregate(
            company=command.company,
            email=command.email,
            password=command.password,
        )
        user.create()

        await domain_repo.add(user)
        await uow.commit()

        return user.id


async def update_user(command: UpdateUser, uow: UnitOfWork) -> None:
    """Handler para atualização de usuário."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = uow.domain_repo

        user = await domain_repo.get_by_email(
            email=command.email,
        )
        user.update(email=command.new_email, password=command.new_password)

        await domain_repo.add(user)
        await uow.commit()


async def delete_user(command: DeleteUser, uow: UnitOfWork) -> None:
    """Handler para exclusão de usuário."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = uow.domain_repo

        user = await domain_repo.get_by_email(
            email=command.email,
        )
        user.delete()

        await domain_repo.remove(user)
        await uow.commit()


async def user_created(event: UserCreated, uow: UnitOfWork) -> None:
    """Handler para o evento de usuário criado."""
    logger.info(f"Event UserCreated for user: {event.id} received")


async def user_updated(event: UserUpdated, uow: UnitOfWork) -> None:
    """Handler para o evento de usuário atualizado."""
    logger.info(f"Event UserUpdated for user: {event.id} received")


async def user_deleted(event: UserDeleted, uow: UnitOfWork) -> None:
    """Handler para o evento de usuário excluído."""
    logger.info(f"Event UserDeleted for user {event.id} received")
