"""Módulo de eventos do domínio Company."""

from dataclasses import dataclass
from uuid import UUID

from messagebus.messagebus import Event


@dataclass
class CompanyCreated(Event):
    """Evento emitido quando uma empresa é criada."""

    id: UUID


@dataclass
class CompanyUpdated(Event):
    """Evento emitido quando uma empresa é atualizada."""

    id: UUID


@dataclass
class CompanyDeleted(Event):
    """Evento emitido quando uma empresa é excluída."""

    id: UUID
