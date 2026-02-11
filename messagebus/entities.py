"""Módulo de entidades base do barramento de mensagens."""

import hashlib
import os
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from business_contexts.consts import pwd_context, AES_KEY

if TYPE_CHECKING:
    from messagebus.messagebus import Event


class UserBase(BaseModel):
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

    def add_event(self, event: "Event") -> None:
        """Adiciona um evento à lista de eventos do agregado."""
        from messagebus.messagebus import Event

        assert issubclass(type(event), Event)
        self.events.append(event)


@dataclass
class UserSecurity:
    """Mixin de segurança para operações com senha e email do usuário."""

    _password_hash: str | None = None

    def verify_password(self, password: str) -> bool:
        """Verifica se a senha informada confere com o hash armazenado."""
        passwords_match = pwd_context.verify(secret=password, hash=self._password_hash)
        return passwords_match

    @staticmethod
    def encrypt_password(password: str) -> str:
        """Criptografa a senha usando bcrypt."""
        encrypted_password = pwd_context.hash(secret=password)
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
