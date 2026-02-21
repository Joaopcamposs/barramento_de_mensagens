"""Testes unitários dos endpoints de segurança."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.entrypoints.api import security as security_api


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

        form_data = SimpleNamespace(username="user@example.com", password="secret")
        result = await security_api.login_for_access_token(form_data)  # type: ignore[arg-type]
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
        """Dispara HTTPException quando autenticação falha."""
        bus = SimpleNamespace(handle=AsyncMock(return_value=None))
        monkeypatch.setattr(security_api, "bootstrap", lambda **_: bus)

        with pytest.raises(Exception):
            await security_api.login_for_access_token(
                SimpleNamespace(username="bad", password="bad")
            )  # type: ignore[arg-type]
