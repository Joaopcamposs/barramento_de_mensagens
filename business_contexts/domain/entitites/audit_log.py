"""Módulo da entidade de leitura AuditLog."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditLog:
    """Entidade de leitura que representa um registro de auditoria."""

    id: UUID
    entity_type: str
    entity_id: UUID
    operation: str
    created_at: datetime
    user_id: UUID | None = None
    old_data: dict | None = None
    new_data: dict | None = None
