from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from messagebus.messagebus import Event


class UserBase(BaseModel):
    """Modelo base de usuário com informações mínimas."""

    company: UUID


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

    events: list["Event"] = field(default_factory=list)
    _operation_type: OperationType | None = None

    def add_event(self, event: "Event") -> None:
        """Adiciona um evento à lista de eventos do agregado."""
        from messagebus.messagebus import Event

        assert issubclass(type(event), Event)
        self.events.append(event)
