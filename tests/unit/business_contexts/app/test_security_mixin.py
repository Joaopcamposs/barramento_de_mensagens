"""Testes unitários do mixin de segurança do usuário."""

from dataclasses import dataclass
from datetime import timedelta

import uuid7

from libs.security import UserSecurity


class TestUserSecurityToken:
    """Testes para geração de token com expiração customizada."""

    @dataclass
    class DummySecurity(UserSecurity):
        """Implementação mínima para exercitar métodos do mixin."""

    def test_generate_token_with_custom_expiration(self) -> None:
        """Usa expires_delta no token gerado em vez do padrão."""
        token = self.DummySecurity.generate_token(
            user_id=uuid7.create(),
            company_id=uuid7.create(),
            expires_delta=timedelta(minutes=5),
        )

        assert token.token_type == "bearer"
        assert isinstance(token.access_token, str)
        assert isinstance(token.refresh_token, str)
