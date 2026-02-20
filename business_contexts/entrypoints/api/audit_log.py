"""Módulo de endpoints da API para AuditLog."""

from uuid import UUID

from fastapi import APIRouter, Depends

from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.views.audit_log import view_audit_log
from business_contexts.entrypoints.schemas.audit_log import ReadAuditLogSchema
from business_contexts.services.handlers.security import current_user, get_current_user

router = APIRouter(
    prefix="/v1",
    tags=["Audit Log"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/audit-log", response_model=list[ReadAuditLogSchema])
async def get_audit_logs(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
) -> list[ReadAuditLogSchema]:
    """
    Consulta registros de auditoria.

    Filtros opcionais:
    - **entity_type**: Tipo da entidade (Company, User).
    - **entity_id**: UUID da entidade específica (requer entity_type).

    Sem filtros retorna todos os registros do tenant.
    """
    uow = UnitOfWork(user=current_user.get())
    audit_logs = await view_audit_log(
        uow,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return audit_logs
