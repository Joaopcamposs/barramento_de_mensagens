"""Testes unitários do mixin de segurança do usuário."""

from dataclasses import dataclass
from datetime import timedelta

import uuid7

from business_contexts.security import UserSecurity


class TestUserSecurityToken:
    """Testes para geração de token com expiração customizada."""

    @dataclass
    class DummySecurity(UserSecurity):
        """Implementação mínima para exercitar métodos do mixin."""

    def test_generate_token_with_custom_expiration(self) -> None:
        """Usa expires_delta no token gerado em vez do padrão."""
        security = self.DummySecurity()
        encrypted = security.encrypt_email("user@example.com")

        token = security.generate_token(
            company_id=uuid7.create(),
            encrypted_email=encrypted,
            expires_delta=timedelta(minutes=5),
        )

        assert token.token_type == "bearer"
        assert isinstance(token.access_token, str)
