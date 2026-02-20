"""Mapeamento ORM da tabela audit_log."""

from sqlalchemy import Column, DateTime, Index, String, Table, func, UUID
from sqlalchemy.dialects.postgresql import JSONB

from business_contexts.domain.aggregate.audit_log import AuditLog
from infra.database import mapper_registry

audit_log = Table(
    "audit_log",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("entity_type", String(100), nullable=False),
    Column("entity_id", UUID, nullable=False),
    Column("operation", String(20), nullable=False),
    Column("old_data", JSONB, nullable=True),
    Column("new_data", JSONB, nullable=True),
    Column("user_id", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_audit_log_entity", "entity_type", "entity_id"),
    Index("ix_audit_log_created_at", "created_at"),
    Index("ix_audit_log_user_id", "user_id"),
)

audit_log_mapper = mapper_registry.map_imperatively(AuditLog, audit_log)
