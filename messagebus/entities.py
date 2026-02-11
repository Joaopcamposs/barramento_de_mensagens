"""Módulo de entidades base do barramento de mensagens."""

import hashlib
import os
from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession

from business_contexts.consts import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AES_KEY,
    ALGORITHM,
    SECRET_KEY,
)
from business_contexts.entrypoints.schemas.security import Token

if TYPE_CHECKING:
    from messagebus.messagebus import Event


@dataclass
class UserBase:
    """Modelo base de usuário com informações mínimas."""

    company: UUID
    id: UUID
    cpf: str | None = None
    email: str | None = None


class DomainRepository(ABC):
    """Repositório abstrato para operações de escrita no domínio."""

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        if session is not None:
            self.session = session


class ViewRepository(ABC):
    """Repositório abstrato para operações de leitura."""

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        if session is not None:
            self.session = session


class OperationType(Enum):
    """Tipos de operação suportados pelo repositório de domínio."""

    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass(kw_only=True)
class Aggregate:
    """Classe base para agregados do domínio."""

    deleted: bool = False

    events: list["Event"] = field(default_factory=list)
    _operation_type: OperationType | None = None

    @property
    def operation_type(self) -> OperationType | None:
        return self._operation_type

    def add_event(self, event: "Event") -> None:
        """Adiciona um evento à lista de eventos do agregado."""
        from messagebus.messagebus import Event

        assert issubclass(type(event), Event)
        self.events.append(event)


@dataclass
class UserSecurity:
    """Mixin de segurança para operações com senha e email do usuário."""

    _password_hash: str | None = None

    @property
    def password_hash(self) -> str | None:
        return self._password_hash

    def verify_password(self, password: str) -> bool:
        """Verifica se a senha informada confere com o hash armazenado."""
        passwords_match = bcrypt.checkpw(
            password.encode()[:72], self._password_hash.encode()
        )
        return passwords_match

    @staticmethod
    def encrypt_password(password: str) -> str:
        """Criptografa a senha usando bcrypt."""
        encrypted_password = bcrypt.hashpw(
            password.encode()[:72], bcrypt.gensalt()
        ).decode()
        return encrypted_password

    @staticmethod
    def hash_email(email: str) -> str:
        """Gera um hash SHA-256 do email para comparação segura."""
        return hashlib.sha256(email.strip().lower().encode()).hexdigest()

    @staticmethod
    def encrypt_email(email: str) -> bytes:
        """Criptografa o email usando AES-GCM."""
        aesgcm = AESGCM(AES_KEY)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, email.encode(), None)
        return nonce + ct

    @staticmethod
    def decrypt_email(email: bytes) -> str:
        """Descriptografa o email usando AES-GCM."""
        aesgcm = AESGCM(AES_KEY)
        nonce, ct = email[:12], email[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()

    def generate_token(
        self,
        company_id: UUID,
        encrypted_email: bytes,
        expires_delta: timedelta | None = None,
    ) -> Token:
        """
        Gera um token JWT para o usuário autenticado.

        Args:
            company_id: UUID da empresa do usuário.
            encrypted_email: Email criptografado do usuário.
            expires_delta: Tempo de expiração customizado (opcional).

        Returns:
            Token JWT com tipo bearer.
        """
        data_to_encode: dict[str, Any] = {
            "email": self.decrypt_email(encrypted_email),
            "id_empresa": str(company_id),
        }
        expire = datetime.now(tz=UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        if expires_delta:
            expire = datetime.now(tz=UTC) + expires_delta
        data_to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return Token(access_token=encoded_jwt, token_type="bearer")
