"""Módulo de eventos do domínio Company."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.entities import AuditableEvent
from messagebus.messagebus import Event


@dataclass(kw_only=True, frozen=True)
class CompanyCreated(AuditableEvent, Event):
    """Evento emitido quando uma empresa é criada."""

    id: UUID


@dataclass(kw_only=True, frozen=True)
class CompanyUpdated(AuditableEvent, Event):
    """Evento emitido quando uma empresa é atualizada."""

    id: UUID


@dataclass(kw_only=True, frozen=True)
class CompanyDeleted(AuditableEvent, Event):
    """Evento emitido quando uma empresa é excluída."""

    id: UUID
