"""Módulo de schemas de entrada/saída para AuditLog."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReadAuditLogSchema(BaseModel):
    """Schema de leitura de registro de auditoria."""

    id: UUID
    entity_type: str
    entity_id: UUID
    operation: str
    old_data: dict | None = None
    new_data: dict | None = None
    user_id: UUID | None = None
    created_at: datetime
