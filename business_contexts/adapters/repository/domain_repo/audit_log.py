"""Módulo do repositório de domínio de AuditLog."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import insert

from messagebus.entities import AuditableEvent, DomainRepository
from business_contexts.domain.aggregate.audit_log import AuditLog
from business_contexts.domain.value_objects.enums import AuditOperation


class AbstractAuditLogDomainRepo(DomainRepository):
    """Repositório abstrato para registros de auditoria."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Inicializa o repositório e o conjunto de agregados rastreados."""
        super().__init__(*args, **kwargs)
        self.seen: set[AuditLog] = set()

    async def add(self, audit_log: AuditLog) -> None:
        """
        Persiste um registro de auditoria no banco de dados.

        Args:
            audit_log: Agregado AuditLog a ser persistido.
        """
        self.seen.add(audit_log)
        await self._add(audit_log)

    @abstractmethod
    async def _add(self, audit_log: AuditLog) -> None:
        """Implementação interna de adição."""
        raise NotImplementedError


class AuditLogDomainRepo(AbstractAuditLogDomainRepo):
    """Repositório de domínio para persistência de registros de auditoria."""

    async def create_from_event(
        self,
        event: AuditableEvent,
        entity_id: UUID,
        operation: AuditOperation,
        user_id: UUID | None = None,
    ) -> AuditLog:
        """
        Cria e persiste um registro de auditoria a partir de um evento auditável.

        Args:
            event: Evento auditável contendo old_data e new_data.
            entity_id: ID da entidade afetada.
            operation: Tipo de operação (CREATE, UPDATE, DELETE).
            user_id: ID do usuário que realizou a operação (opcional).

        Returns:
            Agregado AuditLog criado e adicionado à sessão.
        """
        audit_log = AuditLog.create_aggregate(
            entity_type=event.entity_type,
            entity_id=entity_id,
            operation=operation.value,
            user_id=user_id,
            old_data=event.old_data,
            new_data=event.new_data,
        )
        await self.add(audit_log)
        return audit_log

    async def _add(self, audit_log: AuditLog) -> None:
        """
        Persiste um registro de auditoria no banco de dados.

        Args:
            audit_log: Entidade AuditLog a ser persistida.
        """
        data = {
            "id": audit_log.id,
            "entity_type": audit_log.entity_type,
            "entity_id": audit_log.entity_id,
            "operation": audit_log.operation,
            "old_data": audit_log.old_data,
            "new_data": audit_log.new_data,
            "user_id": audit_log.user_id,
            "created_at": audit_log.created_at,
        }
        await self.session.execute(insert(AuditLog).values(data))
