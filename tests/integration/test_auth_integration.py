"""Testes de integração para o fluxo real de cadastro e autenticação."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest

from business_contexts.consts import SECRET_KEY, ALGORITHM
from business_contexts.domain.commands.company import CreateCompany
from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.excecoes import CredentialsException
from business_contexts.entrypoints.schemas.security import Token
from business_contexts.services.handlers.security import get_current_user
from messagebus.bootstrap import bootstrap


async def _create_company_with_user(
    legal_name: str = "Auth Test Corp",
    email: str = "user@authtest.com",
    password: str = "secret123",
    cpf: str = "12345678901",
) -> UUID:
    """Helper para criar empresa com should_create_user=True (fluxo real de cadastro)."""
    bus = bootstrap(schema="public", raise_event_errors=True)
    return await bus.handle(
        CreateCompany(
            legal_name=legal_name,
            responsible_name="Test User",
            active=True,
            cpf=cpf,
            email=email,
            password=password,
            should_create_user=True,
        )
    )


async def _authenticate(email: str, password: str) -> Token | None:
    """Helper para autenticar um usuário."""
    bus = bootstrap(schema="public", raise_event_errors=True)
    return await bus.handle(AuthenticateUser(email=email, password=password))


class TestCompanyWithUserCreation:
    """Testes do fluxo real: criação de empresa dispara criação de usuário e public_user."""

    async def test_create_company_with_user_returns_uuid(self, engine) -> None:
        """Verifica que criar empresa com should_create_user=True retorna UUID válido."""
        company_id = await _create_company_with_user()
        assert isinstance(company_id, UUID)

    async def test_company_creation_enables_authentication(self, engine) -> None:
        """Verifica que após cadastro real, o login funciona imediatamente."""
        await _create_company_with_user(
            legal_name="Login Ready Corp",
            email="ready@test.com",
            password="mypassword",
        )

        token = await _authenticate("ready@test.com", "mypassword")

        assert isinstance(token, Token)
        assert token.token_type == "bearer"

    async def test_company_creation_without_user_does_not_enable_auth(
        self, engine
    ) -> None:
        """Verifica que should_create_user=False não cria public_user para login."""
        bus = bootstrap(schema="public", raise_event_errors=True)
        await bus.handle(
            CreateCompany(
                legal_name="No User Corp",
                responsible_name="Test",
                active=True,
                cpf="12345678901",
                email="nouser@test.com",
                password="secret123",
                should_create_user=False,
            )
        )

        result = await _authenticate("nouser@test.com", "secret123")
        assert result is None


class TestAuthenticateUser:
    """Testes de integração para o comando AuthenticateUser (login)."""

    async def test_authenticate_valid_credentials_returns_token(self, engine) -> None:
        """Verifica que credenciais válidas retornam Token com access_token."""
        await _create_company_with_user(
            legal_name="Login Corp",
            email="login@test.com",
            password="correct_password",
        )

        token = await _authenticate("login@test.com", "correct_password")

        assert isinstance(token, Token)
        assert token.token_type == "bearer"
        assert len(token.access_token) > 0

    async def test_authenticate_wrong_password_returns_none(self, engine) -> None:
        """Verifica que senha errada retorna None."""
        await _create_company_with_user(
            legal_name="Wrong Pwd Corp",
            email="wrongpwd@test.com",
            password="correct_password",
        )

        result = await _authenticate("wrongpwd@test.com", "wrong_password")

        assert result is None

    async def test_authenticate_nonexistent_email_returns_none(self, engine) -> None:
        """Verifica que email inexistente retorna None."""
        result = await _authenticate("ghost@test.com", "any_password")

        assert result is None

    async def test_authenticate_case_insensitive_email(self, engine) -> None:
        """Verifica que a busca por email é case-insensitive (via hash)."""
        await _create_company_with_user(
            legal_name="Case Corp",
            email="CaseTest@Example.com",
            password="secret123",
        )

        token = await _authenticate("casetest@example.com", "secret123")

        assert isinstance(token, Token)


class TestTokenValidation:
    """Testes de integração para geração e validação do token JWT."""

    async def test_token_contains_correct_email(self, engine) -> None:
        """Verifica que o payload do token contém o email correto."""
        await _create_company_with_user(
            legal_name="Token Email Corp",
            email="tokenemail@test.com",
            password="secret123",
        )

        token = await _authenticate("tokenemail@test.com", "secret123")
        payload = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["email"] == "tokenemail@test.com"

    async def test_token_contains_correct_company_id(self, engine) -> None:
        """Verifica que o payload do token contém o id_empresa correto."""
        company_id = await _create_company_with_user(
            legal_name="Token Co Corp",
            email="tokenco@test.com",
            password="secret123",
        )

        token = await _authenticate("tokenco@test.com", "secret123")
        payload = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["id_empresa"] == str(company_id)

    async def test_token_has_future_utc_expiration(self, engine) -> None:
        """Teste de regressão: exp deve estar no futuro em UTC (bug de timezone corrigido)."""
        await _create_company_with_user(
            legal_name="Token Exp Corp",
            email="tokenexp@test.com",
            password="secret123",
        )

        token = await _authenticate("tokenexp@test.com", "secret123")
        payload = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        assert exp > now

    async def test_token_is_not_immediately_expired(self, engine) -> None:
        """Teste de regressão: token recém-gerado não deve ser rejeitado por expiração."""
        await _create_company_with_user(
            legal_name="Not Expired Corp",
            email="notexpired@test.com",
            password="secret123",
        )

        token = await _authenticate("notexpired@test.com", "secret123")

        payload = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "email" in payload
        assert "id_empresa" in payload

    async def test_token_decode_with_wrong_secret_fails(self, engine) -> None:
        """Verifica que decodificar com chave errada falha."""
        await _create_company_with_user(
            legal_name="Wrong Key Corp",
            email="wrongkey@test.com",
            password="secret123",
        )

        token = await _authenticate("wrongkey@test.com", "secret123")

        with pytest.raises(jwt.exceptions.InvalidSignatureError):
            jwt.decode(token.access_token, "wrong_secret", algorithms=[ALGORITHM])


class TestGetCurrentUser:
    """Testes para get_current_user (validação de token na proteção de rotas)."""

    async def test_invalid_token_raises_credentials_exception(self, engine) -> None:
        """Verifica que token inválido lança CredentialsException."""
        with pytest.raises(CredentialsException):
            await get_current_user("invalid_token_string")

    async def test_expired_token_raises_credentials_exception(self, engine) -> None:
        """Teste de regressão: token expirado deve lançar CredentialsException (não vazar ExpiredSignatureError)."""
        expired_payload = {
            "email": "test@test.com",
            "id_empresa": "some-uuid",
            "exp": datetime.now(tz=timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(CredentialsException):
            await get_current_user(expired_token)

    async def test_token_without_email_raises_credentials_exception(
        self, engine
    ) -> None:
        """Verifica que token sem claim de email lança CredentialsException."""
        payload = {
            "id_empresa": "some-uuid",
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
        }
        token_str = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(CredentialsException):
            await get_current_user(token_str)

    async def test_token_with_wrong_algorithm_raises_credentials_exception(
        self, engine
    ) -> None:
        """Verifica que token assinado com algoritmo diferente lança CredentialsException."""
        payload = {
            "email": "test@test.com",
            "id_empresa": "some-uuid",
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
        }
        token_str = jwt.encode(payload, "other_secret", algorithm="HS384")

        with pytest.raises(CredentialsException):
            await get_current_user(token_str)
