"""Módulo de entidades base do barramento de mensagens."""

import hashlib
import os
from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
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
class AuditableEvent:
    """
    Mixin para eventos que devem gerar registro de auditoria.

    Carrega metadados de auditoria: tipo da entidade, dados anteriores
    e dados novos. Deve ser utilizado junto com Event.
    """

    entity_type: str = ""
    old_data: dict | None = None
    new_data: dict | None = None


@dataclass(kw_only=True)
class AuditBase:
    """
    Classe base com campos de auditoria.

    Pode ser herdada por agregados e entidades comuns. Contém campos de
    criação (criado em/por), edição (editado em/por), exclusão lógica
    (deletado em/por) e o campo ativo. O soft delete é controlado pelo
    campo deleted_at (não nulo = deletado).
    """

    active: bool = True
    created_at: datetime | None = None
    created_by: UUID | None = None
    updated_at: datetime | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None

    @property
    def is_deleted(self) -> bool:
        """Retorna True se a entidade foi marcada como deletada (soft delete)."""
        return self.deleted_at is not None


@dataclass(frozen=True, kw_only=True)
class AuditReadBase:
    """
    Classe base imutável com campos de auditoria para entidades de leitura.

    Versão frozen de AuditBase, destinada a entidades de leitura (somente
    consulta). Garante imutabilidade após a construção do objeto.
    """

    active: bool = True
    created_at: datetime | None = None
    created_by: UUID | None = None
    updated_at: datetime | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None

    @property
    def is_deleted(self) -> bool:
        """Retorna True se a entidade foi marcada como deletada (soft delete)."""
        return self.deleted_at is not None


@dataclass(kw_only=True)
class Aggregate(AuditBase):
    """
    Classe base para agregados do domínio.

    Herda os campos de auditoria de AuditBase e adiciona suporte a
    eventos de domínio e controle de tipo de operação.
    """

    events: list["Event"] = field(default_factory=list)
    _operation_type: OperationType | None = None

    @property
    def operation_type(self) -> OperationType | None:
        return self._operation_type

    def _set_create_audit(self, user_id: UUID | None) -> None:
        """Define os campos de auditoria de criação (created_at e created_by)."""
        self.created_at = datetime.now(timezone.utc)
        self.created_by = user_id

    def _set_update_audit(self, user_id: UUID | None) -> None:
        """Define os campos de auditoria de atualização (updated_at e updated_by)."""
        self.updated_at = datetime.now(timezone.utc)
        self.updated_by = user_id

    def _set_delete_audit(self, user_id: UUID | None) -> None:
        """Define os campos de auditoria de exclusão (deleted_at e deleted_by)."""
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = user_id

    def add_event(self, event: "Event") -> None:
        """Adiciona um evento à lista de eventos do agregado."""
        from messagebus.messagebus import Event

        assert issubclass(type(event), Event)
        self.events.append(event)

    def _track_change(
        self,
        old_data: dict,
        new_data: dict,
        field_name: str,
        new_value: Any,
        serializer: Any = None,
    ) -> None:
        """
        Registra a mudança de um campo nos dicionários de auditoria e aplica o novo valor.

        Args:
            old_data: Dicionário de dados anteriores da auditoria.
            new_data: Dicionário de dados novos da auditoria.
            field_name: Nome do atributo no agregado.
            new_value: Novo valor a ser aplicado (ignorado se None).
            serializer: Função opcional para serializar o valor (ex: str para datas).
        """
        if new_value is None:
            return
        current = getattr(self, field_name)
        old_data[field_name] = serializer(current) if serializer else current
        new_data[field_name] = serializer(new_value) if serializer else new_value
        setattr(self, field_name, new_value)


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
