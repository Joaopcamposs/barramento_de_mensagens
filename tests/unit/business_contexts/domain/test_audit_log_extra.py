"""Testes complementares do agregado AuditLog."""

import uuid7

from business_contexts.domain.aggregate.audit_log import AuditLog
from messagebus.entities import OperationType


class TestAuditLogAggregate:
    """Testes para agregado de auditoria."""

    def test_create_aggregate_sets_insert_operation_and_timestamp(self) -> None:
        """Cria agregado de auditoria já marcado para inserção."""
        entity_id = uuid7.create()
        log = AuditLog.create_aggregate(
            entity_type="User",
            entity_id=entity_id,
            operation="CREATE",
            old_data=None,
            new_data={"email": "user@example.com"},
        )

        assert log.entity_id == entity_id
        assert log.operation_type == OperationType.INSERT
        assert log.created_at is not None

    def test_hash_uses_identifier(self) -> None:
        """Mantém hash estável baseado no id do agregado."""
        log = AuditLog.create_aggregate(
            entity_type="Company",
            entity_id=uuid7.create(),
            operation="UPDATE",
        )
        assert hash(log) == hash(log.id)
