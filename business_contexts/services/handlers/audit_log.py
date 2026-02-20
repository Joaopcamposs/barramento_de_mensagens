"""Módulo de handlers de eventos para registro de auditoria."""

from typing import cast
from uuid import UUID

from messagebus.entities import AuditableEvent
from messagebus.messagebus import Event, logger
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.repository.domain_repo.audit_log import AuditLogDomainRepo
from business_contexts.domain.entitites.audit_log import AuditLog
from business_contexts.domain.value_objects.enums import AuditOperation
from business_contexts.domains import Domain


async def _persist_audit_log(
    event: Event,
    operation: AuditOperation,
    uow: UnitOfWork,
) -> AuditLog | None:
    """
    Lógica comum para persistir um registro de auditoria a partir de um evento.

    Verifica se o evento é auditável e, em caso positivo, persiste o registro
    na tabela audit_log.

    Args:
        event: Evento de domínio recebido pelo handler.
        operation: Tipo de operação (CREATE, UPDATE, DELETE).
        uow: Unit of Work com sessão e usuário autenticado.

    Returns:
        AuditLog persistido ou None se o evento não for auditável.
    """
    if not isinstance(event, AuditableEvent) or not event.entity_type:
        return None

    async with uow(Domain.audit_log) as uow:
        repo: AuditLogDomainRepo = cast(AuditLogDomainRepo, uow.domain_repo)

        user_id: UUID | None = uow.user.id if uow.user else None
        audit_log = await repo.create_from_event(
            event=event,
            entity_id=event.id,
            operation=operation,
            user_id=user_id,
        )
        await uow.commit()

    logger.info(
        f"AuditLog {operation.value} for {event.entity_type} {event.id}: {audit_log.id}"
    )
    return audit_log


async def audit_entity_created(event: Event, uow: UnitOfWork) -> None:
    """Handler para registrar auditoria de criação de entidade."""
    await _persist_audit_log(event, AuditOperation.CREATE, uow)


async def audit_entity_updated(event: Event, uow: UnitOfWork) -> None:
    """Handler para registrar auditoria de atualização de entidade."""
    await _persist_audit_log(event, AuditOperation.UPDATE, uow)


async def audit_entity_deleted(event: Event, uow: UnitOfWork) -> None:
    """Handler para registrar auditoria de exclusão de entidade."""
    await _persist_audit_log(event, AuditOperation.DELETE, uow)
