"""Módulo de endpoints da API para AuditLog."""

from uuid import UUID

from fastapi import APIRouter, Depends

from business_contexts.bootstrap import bootstrap_apis
from messagebus.messagebus import MessageBus
from business_contexts.adapters.views.audit_log import view_audit_log
from business_contexts.domain.value_objects.enums import EntityType
from business_contexts.entrypoints.schemas.audit_log import ReadAuditLogSchema
from business_contexts.services.handlers.security import get_current_user

router = APIRouter(
    prefix="/api",
    tags=["Audit Log"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/audit-log", response_model=list[ReadAuditLogSchema])
async def get_audit_logs(
    bus: MessageBus = Depends(bootstrap_apis),
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
) -> list[ReadAuditLogSchema]:
    """
    Consulta registros de auditoria.

    Filtros opcionais:
    - **entity_type**: Tipo da entidade (Company, User, AuditLog).
    - **entity_id**: UUID da entidade específica (requer entity_type).

    Sem filtros retorna todos os registros do tenant.
    """
    audit_logs = await view_audit_log(
        bus.uow,
        entity_type=entity_type.value if entity_type else None,
        entity_id=entity_id,
    )
    return audit_logs
