"""Testes unitários para helpers de segurança."""

from dataclasses import dataclass
from datetime import timedelta

import jwt
import pytest
import uuid7

import libs.security as security_module
from libs.consts import ALGORITHM, SECRET_KEY
from libs.security import UserSecurity


@dataclass
class DummySecurity(UserSecurity):
    """Implementação mínima para exercitar o mixin."""


def test_verify_password_handles_missing_or_invalid_hash() -> None:
    """Retorna False quando não há hash ou o hash armazenado é inválido."""
    assert DummySecurity().verify_password("secret") is False
    assert DummySecurity(_password_hash="invalid").verify_password("secret") is False


def test_password_hash_round_trip() -> None:
    """Valida senha correta e rejeita senha incorreta."""
    security = DummySecurity(_password_hash=UserSecurity.encrypt_password("secret"))

    assert security.verify_password("secret") is True
    assert security.verify_password("wrong") is False


def test_lookup_helpers_are_normalized_and_deterministic() -> None:
    """Gera lookups determinísticos com normalização de email e CPF."""
    assert UserSecurity.normalize_email(" User@Example.COM ") == "user@example.com"
    assert UserSecurity.normalize_cpf("123.456.789-09") == "12345678909"
    assert UserSecurity.compute_email_lookup_hmac(
        "User@Example.COM"
    ) == UserSecurity.compute_email_lookup_hmac(" user@example.com ")
    assert UserSecurity.compute_cpf_lookup_hmac(
        "123.456.789-09"
    ) == UserSecurity.compute_cpf_lookup_hmac("12345678909")


def test_encrypt_text_round_trip() -> None:
    """Criptografa e descriptografa texto arbitrário."""
    encrypted = UserSecurity.encrypt_text("valor sensível")

    assert encrypted != "valor sensível".encode()
    assert UserSecurity.decrypt_text(encrypted) == "valor sensível"


def test_generate_token_pair_and_decode_refresh_token() -> None:
    """Gera par de tokens e decodifica o refresh token."""
    user_id = uuid7.create()
    company_id = uuid7.create()

    token = UserSecurity.generate_token_pair(
        user_id=user_id,
        company_id=company_id,
        expires_delta=timedelta(minutes=1),
    )

    assert token.token_type == "bearer"
    assert token.refresh_token is not None
    access_payload = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM])
    refresh_payload = UserSecurity.decode_refresh_token(token.refresh_token)
    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["sub"] == str(user_id)


def test_decode_refresh_token_rejects_access_token() -> None:
    """Rejeita token JWT que não é do tipo refresh."""
    token = UserSecurity.generate_token_pair(
        user_id=uuid7.create(),
        company_id=uuid7.create(),
    )

    with pytest.raises(jwt.exceptions.InvalidTokenError):
        UserSecurity.decode_refresh_token(token.access_token)


def test_decode_base64_key_rejects_invalid_values() -> None:
    """Retorna None para valores base64 ausentes, inválidos ou de tamanho incompatível."""
    assert security_module._decode_base64_key("") is None
    assert security_module._decode_base64_key("not-base64") is None
    assert security_module._decode_base64_key("YQ==") is None


def test_get_aes_key_accepts_raw_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aceita chave AES textual com tamanho compatível."""
    security_module.get_aes_key.cache_clear()
    monkeypatch.setenv("AES_KEY", "*" * 32)

    try:
        assert security_module.get_aes_key() == b"*" * 32
    finally:
        security_module.get_aes_key.cache_clear()


def test_get_aes_key_uses_test_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Usa chave determinística de fallback durante testes."""
    security_module.get_aes_key.cache_clear()
    monkeypatch.setenv("AES_KEY", "")

    try:
        assert len(security_module.get_aes_key()) == 32
    finally:
        security_module.get_aes_key.cache_clear()


def test_get_aes_key_rejects_invalid_runtime_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rejeita chave inválida quando não está em runtime de teste."""
    security_module.get_aes_key.cache_clear()
    monkeypatch.setenv("AES_KEY", "")
    monkeypatch.setattr(security_module, "_is_test_runtime", lambda: False)

    try:
        with pytest.raises(ValueError, match="AES_KEY"):
            security_module.get_aes_key()
    finally:
        security_module.get_aes_key.cache_clear()


def test_is_test_runtime_returns_boolean() -> None:
    """Retorna um booleano para indicar runtime de testes."""
    assert isinstance(security_module._is_test_runtime(), bool)
