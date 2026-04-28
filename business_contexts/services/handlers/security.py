"""Módulo de handlers de segurança e autenticação."""

from contextvars import ContextVar
from typing import Annotated, cast
from uuid import UUID

import jwt
from fastapi import Depends
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from business_contexts.adapters.repository.view_repo.user import UserViewRepo
from business_contexts.consts import ALGORITHM, SECRET_KEY, oauth2_scheme
from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.entitites.user import User
from business_contexts.domain.excecoes import (
    CredentialsException,
    UserNotFound,
    InvalidCredentials,
)
from business_contexts.entrypoints.schemas.security import Token
from business_contexts.domains import Domain
from messagebus.unity_of_work import UnitOfWork

current_user: ContextVar["User"] = ContextVar("current_user")


async def authenticate_user(command: AuthenticateUser, uow: UnitOfWork) -> Token | None:
    """
    Autentica um usuário pelo email e senha via schema do tenant.

    Args:
        command: Comando de autenticação com email e senha.
        uow: Unit of Work para gerenciar a sessão.

    Returns:
        Token JWT se autenticado com sucesso, None caso contrário.
    """
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = cast(UserViewRepo, uow.view_repo)
        public_user = await view_repo.get_public_user_by_email(command.email)

    if not public_user:
        raise UserNotFound

    tenant_uow = UnitOfWork(schema=str(public_user.company), read_only=True)
    async with tenant_uow(Domain.user) as tenant_ctx:
        tenant_view_repo = tenant_ctx.get_view_repo(UserViewRepo)
        user = await tenant_view_repo.get_by_id(public_user.id)
        if not user:
            raise UserNotFound
        if not user.verify_password(command.password):
            raise InvalidCredentials

        return user.generate_token(
            user_id=user.id,
            company_id=user.company,
        )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Obtém o usuário autenticado a partir do token JWT.

    Args:
        token: Token JWT do cabeçalho Authorization.

    Returns:
        Entidade User do usuário autenticado.

    Raises:
        CredentialsException: Se o token for inválido ou o usuário não for encontrado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        company_id: str | None = payload.get("id_empresa")
        if user_id is None or company_id is None:
            raise CredentialsException()
    except (InvalidTokenError, ValidationError):
        raise CredentialsException()

    uow = UnitOfWork(schema=str(company_id), read_only=True)
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = cast(UserViewRepo, uow.view_repo)
        user = await view_repo.get_by_id(UUID(user_id))

    if user is None:
        raise CredentialsException()

    current_user.set(user)

    return user


async def get_current_admin_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Obtém o usuário autenticado e garante privilégios de administrador.

    Args:
        token: Token JWT do cabeçalho Authorization.

    Returns:
        Entidade User do usuário autenticado.

    Raises:
        CredentialsException: Se o token for inválido, o usuário não for encontrado
            ou não tiver perfil administrador.
    """
    user = await get_current_user(token)
    if not user.admin:
        raise CredentialsException()
    current_user.set(user)
    return user
