"""Mixin de segurança para operações com senha e email do usuário."""

import base64
import binascii
import hashlib
import hmac
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from libs.consts import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    LOOKUP_HMAC_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from business_contexts.entrypoints.schemas.security import Token


@dataclass
class UserSecurity:
    """Mixin de segurança para operações com senha e email do usuário."""

    _password_hash: str | None = None

    @property
    def password_hash(self) -> str | None:
        """Retorna o hash de senha armazenado para o usuário."""
        return self._password_hash

    def verify_password(self, password: str) -> bool:
        """Verifica se a senha informada confere com o hash armazenado."""
        if not self._password_hash:
            return False
        try:
            return bcrypt.checkpw(
                password.encode()[:72],
                self._password_hash.encode(),
            )
        except ValueError:
            return False

    @staticmethod
    def encrypt_password(password: str) -> str:
        """Criptografa a senha usando bcrypt."""
        encrypted_password = bcrypt.hashpw(
            password.encode()[:72], bcrypt.gensalt()
        ).decode()
        return encrypted_password

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normaliza email para comparacoes deterministicas."""
        return email.strip().lower()

    @staticmethod
    def normalize_cpf(cpf: str) -> str:
        """Normaliza CPF mantendo apenas digitos."""
        return re.sub(r"\D", "", cpf)

    @staticmethod
    def _lookup_hmac(value: str) -> str:
        """Gera HMAC-SHA256 deterministicamente com chave dedicada de lookup."""
        return hmac.new(
            LOOKUP_HMAC_KEY.encode(),
            value.encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def compute_email_lookup_hmac(email: str) -> str:
        """Gera o HMAC de lookup para email normalizado."""
        return UserSecurity._lookup_hmac(UserSecurity.normalize_email(email))

    @staticmethod
    def compute_cpf_lookup_hmac(cpf: str) -> str:
        """Gera o HMAC de lookup para CPF normalizado."""
        return UserSecurity._lookup_hmac(UserSecurity.normalize_cpf(cpf))

    @staticmethod
    def encrypt_email(email: str) -> bytes:
        """Criptografa o email usando AES-GCM."""
        aesgcm = AESGCM(get_aes_key())
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, email.encode(), None)
        return nonce + ct

    @staticmethod
    def decrypt_email(email: bytes) -> str:
        """Descriptografa o email usando AES-GCM."""
        aesgcm = AESGCM(get_aes_key())
        nonce, ct = email[:12], email[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()

    @staticmethod
    def encrypt_text(value: str) -> bytes:
        """Criptografa um texto arbitrario usando AES-GCM."""
        aesgcm = AESGCM(get_aes_key())
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, value.encode(), None)
        return nonce + ct

    @staticmethod
    def decrypt_text(value: bytes) -> str:
        """Descriptografa um texto arbitrario usando AES-GCM."""
        aesgcm = AESGCM(get_aes_key())
        nonce, ct = value[:12], value[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()

    @staticmethod
    def generate_token(
        user_id: UUID,
        company_id: UUID,
        expires_delta: timedelta | None = None,
    ) -> Token:
        """
        Gera um par de tokens JWT (access + refresh) para o usuário autenticado.

        O access_token é curto (definido por ACCESS_TOKEN_EXPIRE_MINUTES).
        O refresh_token é longo (definido por REFRESH_TOKEN_EXPIRE_DAYS) e
        contém um claim ``type: refresh`` para diferenciá-lo.

        Args:
            user_id: UUID do usuário autenticado.
            company_id: UUID da empresa do usuário.
            expires_delta: Tempo de expiração customizado para o access_token.

        Returns:
            Token JWT com access_token, refresh_token e tipo bearer.
        """
        now = datetime.now(tz=UTC)

        # Access token
        access_expire = now + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        access_payload: dict[str, Any] = {
            "sub": str(user_id),
            "id_empresa": str(company_id),
            "type": "access",
            "exp": access_expire,
        }
        access_jwt = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)

        # Refresh token
        refresh_expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_payload: dict[str, Any] = {
            "sub": str(user_id),
            "id_empresa": str(company_id),
            "type": "refresh",
            "exp": refresh_expire,
        }
        refresh_jwt = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

        return Token(
            access_token=access_jwt,
            refresh_token=refresh_jwt,
            token_type="bearer",
        )

    @staticmethod
    def decode_refresh_token(token: str) -> dict[str, Any]:
        """
        Decodifica e valida um refresh token JWT.

        Args:
            token: Refresh token JWT.

        Returns:
            Payload do token com sub, id_empresa, type.

        Raises:
            InvalidTokenError: Se o token estiver expirado, inválido ou não for do tipo refresh.
        """
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise jwt.exceptions.InvalidTokenError("Token is not a refresh token")
        return payload


@lru_cache(maxsize=1)
def get_aes_key() -> bytes:
    """Resolve a chave AES a partir da configuração atual com fallback seguro para testes."""
    configured_key = os.getenv("AES_KEY", "")
    decoded_key = _decode_base64_key(configured_key)
    if decoded_key is not None:
        return decoded_key

    raw_key = configured_key.encode()
    if len(raw_key) in {16, 24, 32}:
        return raw_key

    if _is_test_runtime():
        return hashlib.sha256(b"kontas-test-aes-key").digest()

    raise ValueError(
        "A variável AES_KEY deve conter uma chave AES válida em base64 ou texto cru com 16, 24 ou 32 bytes."
    )


def _decode_base64_key(value: str) -> bytes | None:
    """Decodifica uma chave base64 e valida se o tamanho é compatível com AES-GCM."""
    if not value:
        return None
    try:
        decoded = base64.b64decode(value.encode(), validate=True)
    except binascii.Error:
        return None
    if len(decoded) in {16, 24, 32}:
        return decoded
    return None


def _is_test_runtime() -> bool:
    """Indica se o processo atual está executando a suíte de testes."""
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
