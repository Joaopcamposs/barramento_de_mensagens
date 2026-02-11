"""Módulo de handlers de segurança e autenticação."""

from contextvars import ContextVar
from typing import Annotated

import jwt
from fastapi import Depends
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from business_contexts.adapters.repository.view_repo.user import UserViewRepo
from business_contexts.consts import oauth2_scheme, SECRET_KEY, ALGORITHM
from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.entitites.user import User
from business_contexts.domain.excecoes import CredentialsException
from business_contexts.entrypoints.schemas.security import Token
from messagebus.domains import Domain
from messagebus.unity_of_work import UnitOfWork

current_user: ContextVar["User"] = ContextVar("current_user")


async def authenticate_user(command: AuthenticateUser, uow: UnitOfWork) -> Token | None:
    """
    Autentica um usuário pelo email e senha via usuário público.

    Args:
        command: Comando de autenticação com email e senha.
        uow: Unit of Work para gerenciar a sessão.

    Returns:
        Token JWT se autenticado com sucesso, None caso contrário.
    """
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = uow.view_repo

        user = await view_repo.get_public_user_by_email(command.email)
        if not user:
            return None
        if not user.verify_password(command.password):
            return None

        return user.generate_token(
            company_id=user.company,
            encrypted_email=user.email_encrypted,
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
        email: str | None = payload.get("email")
        company_id: str | None = payload.get("id_empresa")
        if email is None:
            raise CredentialsException()
    except (InvalidTokenError, ValidationError):
        raise CredentialsException()

    uow = UnitOfWork(schema=str(company_id))
    async with uow(Domain.user) as uow:
        view_repo: UserViewRepo = uow.view_repo
        user = await view_repo.get_by_email(email)

    if user is None:
        raise CredentialsException()

    current_user.set(user)

    return user
