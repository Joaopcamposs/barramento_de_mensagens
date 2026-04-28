"""Módulo de handlers de comandos e eventos do domínio User."""

from typing import cast
from uuid import UUID

from business_contexts.adapters.repository.domain_repo.user import (
    UserDomainRepo,
)
from business_contexts.adapters.repository.view_repo.user import UserViewRepo
from business_contexts.domain.aggregate.user import PublicUser
from business_contexts.domain.commands.user import (
    CreateUser,
    DeleteUser,
    UpdateUser,
)
from business_contexts.domain.events.user import (
    TimeToCreateCompanyAdminUser,
    TimeToCreateInitialCompanyUser,
    UserCreated,
    UserDeleted,
    UserUpdated,
)
from business_contexts.domains import Domain
from messagebus.messagebus import logger
from messagebus.unity_of_work import UnitOfWork


async def create_user(
    command_or_event: CreateUser
    | TimeToCreateInitialCompanyUser
    | TimeToCreateCompanyAdminUser,
    uow: UnitOfWork,
) -> UUID:
    """Handler para criação de usuário."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = cast(UserDomainRepo, uow.domain_repo)

        user = await domain_repo.create_aggregate(
            company=command_or_event.company,
            email=command_or_event.email,
            cpf=command_or_event.cpf,
            password=command_or_event.password,
            active=command_or_event.active,
            admin=command_or_event.admin,
        )
        user.create(user_id=uow.user_id)

        await domain_repo.add(user)
        await uow.commit()

        return user.id


async def update_user(command: UpdateUser, uow: UnitOfWork) -> None:
    """Handler para atualização de usuário."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = cast(UserDomainRepo, uow.domain_repo)

        user = await domain_repo.get_by_email(
            email=command.email,
        )
        user.update(
            email=command.new_email,
            password=command.new_password,
            active=command.new_active,
            admin=command.new_admin,
            user_id=uow.user_id,
        )

        await domain_repo.add(user)
        await uow.commit()


async def delete_user(command: DeleteUser, uow: UnitOfWork) -> None:
    """Handler para exclusão (soft delete) de usuário."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = cast(UserDomainRepo, uow.domain_repo)

        user = await domain_repo.get_by_email(
            email=command.email,
        )
        user.delete(user_id=uow.user_id)

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


async def create_public_user(event: UserCreated, uow: UnitOfWork) -> UUID:
    """Handler para criação do usuário público após criação do usuário privado."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = cast(UserDomainRepo, uow.domain_repo)
        view_repo: UserViewRepo = cast(UserViewRepo, uow.view_repo)

        user = await view_repo.get_by_id(id=event.id)
        public_user = PublicUser.create_registration_aggregate(user=user)

        await domain_repo.add_public_user(
            public_user=public_user,
        )
        await uow.commit()

    return public_user.id


async def update_public_user(event: UserUpdated, uow: UnitOfWork) -> None:
    """Handler para atualização do CPF no usuário público após atualização do privado."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = cast(UserDomainRepo, uow.domain_repo)
        view_repo: UserViewRepo = cast(UserViewRepo, uow.view_repo)

        private_user = await view_repo.get_by_id(id=event.id)

        public_user = await domain_repo.get_public_user_by_id(id=event.id)
        if public_user:
            public_user.update_cpf(cpf=private_user.cpf)
            await domain_repo.update_public_user_cpf(public_user=public_user)
        await uow.commit()


async def remove_public_user(event: UserDeleted, uow: UnitOfWork) -> None:
    """Handler para remoção do usuário público após exclusão do usuário privado."""
    async with uow(Domain.user) as uow:
        domain_repo: UserDomainRepo = cast(UserDomainRepo, uow.domain_repo)

        public_user = await domain_repo.get_public_user_by_id(id=event.id)
        if public_user:
            await domain_repo.remove_public_user(public_user=public_user)
        await uow.commit()
