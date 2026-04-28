"""Testes unitários dos endpoints de segurança."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
import uuid7

from business_contexts.domain.excecoes import InvalidCredentials, InvalidRefreshToken
from business_contexts.entrypoints.api import security as security_api


def make_request() -> Request:
    """Cria um Request real para endpoints decorados pelo SlowAPI."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/token",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


class TestSecurityApi:
    """Testes para endpoints de autenticação."""

    @pytest.mark.asyncio
    async def test_login_for_access_token_and_user_me(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Retorna token em login válido e usuário autenticado no endpoint me."""
        token_model = security_api.Token(access_token="jwt", token_type="bearer")
        bus = SimpleNamespace(handle=AsyncMock(return_value=token_model))
        monkeypatch.setattr(security_api, "bootstrap", lambda **_: bus)
        monkeypatch.setattr(security_api, "verify_turnstile", AsyncMock())

        form_data = SimpleNamespace(username="user@example.com", password="secret")
        request = make_request()
        result = await security_api.login_for_access_token(request, form_data)  # type: ignore[arg-type]
        assert result.access_token == "jwt"

        current = SimpleNamespace(
            id=uuid7.create(), company=uuid7.create(), email="user@example.com"
        )
        me = await security_api.read_users_me(current)  # type: ignore[arg-type]
        assert me is current

    @pytest.mark.asyncio
    async def test_login_for_access_token_raises_on_invalid_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Propaga erro de credenciais quando autenticação falha."""
        bus = SimpleNamespace(handle=AsyncMock(side_effect=InvalidCredentials))
        monkeypatch.setattr(security_api, "bootstrap", lambda **_: bus)
        monkeypatch.setattr(security_api, "verify_turnstile", AsyncMock())

        with pytest.raises(InvalidCredentials):
            await security_api.login_for_access_token(
                make_request(),
                SimpleNamespace(username="bad", password="bad"),
            )  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_refresh_access_token_returns_new_pair(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Renova token usando usuário ativo do tenant."""
        user_id = uuid7.create()
        company_id = uuid7.create()
        user = SimpleNamespace(
            id=user_id,
            company=company_id,
            email="user@example.com",
            active=True,
            generate_token=lambda user_id, company_id: security_api.Token(
                access_token=f"jwt-{user_id}",
                token_type="bearer",
                refresh_token=f"refresh-{company_id}",
            ),
        )
        monkeypatch.setattr(
            security_api.UserSecurity,
            "decode_refresh_token",
            staticmethod(lambda _: {"sub": str(user_id), "id_empresa": str(company_id)}),
        )
        get_tenant_user = AsyncMock(return_value=user)
        monkeypatch.setattr(security_api, "get_tenant_user", get_tenant_user)

        token = await security_api.refresh_access_token(
            make_request(),
            security_api.RefreshTokenRequest(refresh_token="valid"),
        )

        assert token.access_token == f"jwt-{user_id}"
        get_tenant_user.assert_awaited_once_with(schema=str(company_id), user_id=user_id)

    @pytest.mark.asyncio
    async def test_refresh_access_token_rejects_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rejeita refresh token inválido antes de consultar o tenant."""
        monkeypatch.setattr(
            security_api.UserSecurity,
            "decode_refresh_token",
            staticmethod(lambda _: (_ for _ in ()).throw(ValueError("invalid"))),
        )

        with pytest.raises(InvalidRefreshToken):
            await security_api.refresh_access_token(
                make_request(),
                security_api.RefreshTokenRequest(refresh_token="invalid"),
            )
