"""Módulo de endpoints da API para autenticação e segurança."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError

from business_contexts.adapters.views.user import get_tenant_user
from business_contexts.bootstrap import bootstrap
from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.entitites.user import User
from business_contexts.domain.excecoes import InvalidRefreshToken
from business_contexts.entrypoints.schemas.security import RefreshTokenRequest, Token
from business_contexts.entrypoints.schemas.user import ReadUserSchema
from business_contexts.services.handlers.security import get_current_user
from libs.logger import fingerprint, logger
from libs.rate_limit import limiter
from libs.security import UserSecurity
from libs.turnstile import verify_turnstile

security_router = APIRouter(prefix="/api", tags=["Login"])


@security_router.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    x_turnstile_token: Annotated[str | None, Header(alias="x-turnstile-token")] = None,
) -> Token:
    """Autentica o usuário e retorna um token JWT."""
    await verify_turnstile(
        x_turnstile_token,
        request.client.host if request.client else None,
    )
    bus = bootstrap()

    token = cast(
        Token,
        await bus.handle(
            AuthenticateUser(
                email=form_data.username,
                password=form_data.password,
            )
        ),
    )
    logger.info(
        "operation=login status=success email_hash=%s",
        fingerprint(form_data.username),
    )
    return token


@security_router.post("/token/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_access_token(
    request: Request,
    body: RefreshTokenRequest,
) -> Token:
    """Renova o access token usando um refresh token válido."""
    try:
        payload = UserSecurity.decode_refresh_token(body.refresh_token)
        user_id = UUID(str(payload["sub"]))
        company_id = UUID(str(payload["id_empresa"]))
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise InvalidRefreshToken from error

    user = await get_tenant_user(schema=str(company_id), user_id=user_id)
    if not user or not user.active:
        raise InvalidRefreshToken

    logger.info(
        "operation=token_refresh status=success user_id=%s company_id=%s",
        user_id,
        company_id,
    )
    return user.generate_token(user_id=user.id, company_id=user.company)


@security_router.get("/user/me/", response_model=ReadUserSchema)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Retorna os dados do usuário autenticado."""
    return current_user
