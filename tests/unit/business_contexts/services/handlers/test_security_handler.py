"""Testes unitários dos handlers de segurança."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import jwt
import pytest
import uuid7

from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.excecoes import (
    CredentialsException,
    InvalidCredentials,
    UserNotFound,
)
from business_contexts.entrypoints.schemas.security import Token
from business_contexts.services.handlers import security as security_handlers
from tests.unit.helpers import FakeUoW


class TestSecurityHandlers:
    """Testes para autenticação e resolução de usuário atual."""

    @pytest.mark.asyncio
    async def test_authenticate_user_paths(self) -> None:
        """Valida autenticação para usuário inexistente, senha inválida e sucesso."""
        command = AuthenticateUser(email="user@example.com", password="secret")

        view_repo_none = SimpleNamespace(
            get_public_user_by_email=AsyncMock(return_value=None)
        )
        with pytest.raises(UserNotFound):
            await security_handlers.authenticate_user(
                command, FakeUoW(view_repo=view_repo_none)
            )  # type: ignore[arg-type]

        bad_user = SimpleNamespace(verify_password=lambda _: False)
        view_repo_bad = SimpleNamespace(
            get_public_user_by_email=AsyncMock(return_value=bad_user)
        )
        with pytest.raises(InvalidCredentials):
            await security_handlers.authenticate_user(
                command, FakeUoW(view_repo=view_repo_bad)
            )  # type: ignore[arg-type]

        token = Token(access_token="jwt", token_type="bearer")
        good_user = SimpleNamespace(
            company=uuid7.create(),
            email_encrypted=b"enc",
            verify_password=lambda _: True,
            generate_token=lambda **_: token,
        )
        view_repo_good = SimpleNamespace(
            get_public_user_by_email=AsyncMock(return_value=good_user)
        )

        authenticated = await security_handlers.authenticate_user(
            command, FakeUoW(view_repo=view_repo_good)
        )  # type: ignore[arg-type]
        assert authenticated == token

    @pytest.mark.asyncio
    async def test_get_current_user_success_sets_context(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Decodifica token, busca usuário e atualiza ContextVar atual."""
        user = SimpleNamespace(
            id=uuid7.create(), company=uuid7.create(), email="user@example.com"
        )
        fake_uow = FakeUoW(
            view_repo=SimpleNamespace(get_by_email=AsyncMock(return_value=user))
        )

        monkeypatch.setattr(
            security_handlers.jwt,
            "decode",
            lambda token, key, algorithms: {
                "email": "user@example.com",
                "id_empresa": str(user.company),
            },
        )
        monkeypatch.setattr(security_handlers, "UnitOfWork", lambda **_: fake_uow)

        result = await security_handlers.get_current_user("token")

        assert result is user
        assert security_handlers.current_user.get() is user

    @pytest.mark.asyncio
    async def test_get_current_user_raises_on_missing_email(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lança erro de credenciais quando payload não contém email."""
        monkeypatch.setattr(
            security_handlers.jwt,
            "decode",
            lambda token, key, algorithms: {"id_empresa": str(uuid7.create())},
        )

        with pytest.raises(CredentialsException):
            await security_handlers.get_current_user("token")

    @pytest.mark.asyncio
    async def test_get_current_user_raises_on_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Converte exceções de JWT para erro de credenciais."""

        def raise_invalid(*args: Any, **kwargs: Any) -> dict[str, Any]:
            raise jwt.exceptions.InvalidTokenError("bad")

        monkeypatch.setattr(security_handlers.jwt, "decode", raise_invalid)

        with pytest.raises(CredentialsException):
            await security_handlers.get_current_user("token")

    @pytest.mark.asyncio
    async def test_get_current_user_raises_when_user_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Retorna erro de credenciais quando usuário não existe no schema."""
        monkeypatch.setattr(
            security_handlers.jwt,
            "decode",
            lambda token, key, algorithms: {
                "email": "u@example.com",
                "id_empresa": str(uuid7.create()),
            },
        )
        monkeypatch.setattr(
            security_handlers,
            "UnitOfWork",
            lambda **_: FakeUoW(
                view_repo=SimpleNamespace(get_by_email=AsyncMock(return_value=None))
            ),
        )

        with pytest.raises(CredentialsException):
            await security_handlers.get_current_user("token")
