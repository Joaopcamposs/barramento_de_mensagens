"""Módulo do agregado AuditLog."""

from dataclasses import dataclass
from uuid import UUID

import uuid7

from messagebus.entities import Aggregate, OperationType


@dataclass(kw_only=True)
class AuditLog(Aggregate):
    """Agregado que representa um registro de auditoria no domínio."""

    id: UUID
    entity_type: str
    entity_id: UUID
    operation: str
    user_id: UUID | None = None
    old_data: dict | None = None
    new_data: dict | None = None

    def __hash__(self) -> int:
        """Retorna um hash estável baseado no identificador do agregado."""
        return hash(self.id)

    @staticmethod
    def create_aggregate(
        entity_type: str,
        entity_id: UUID,
        operation: str,
        user_id: UUID | None = None,
        old_data: dict | None = None,
        new_data: dict | None = None,
    ) -> "AuditLog":
        """
        Cria uma nova instância do agregado AuditLog.

        Args:
            entity_type: Tipo da entidade auditada.
            entity_id: ID da entidade auditada.
            operation: Operação realizada (CREATE, UPDATE, DELETE).
            user_id: ID do usuário que realizou a operação (opcional).
            old_data: Dados anteriores (opcional).
            new_data: Novos dados (opcional).

        Returns:
            Nova instância de AuditLog com ID gerado.
        """
        audit_log = AuditLog(
            id=uuid7.create(),
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            user_id=user_id,
            old_data=old_data,
            new_data=new_data,
        )
        audit_log.create()
        return audit_log

    def create(self) -> None:
        """Marca o agregado para inserção."""
        self._operation_type = OperationType.INSERT
        self._set_create_audit(user_id=None)
