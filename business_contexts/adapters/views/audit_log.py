"""Módulo de views de consulta de AuditLog."""

from typing import cast
from uuid import UUID

from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.repository.view_repo.audit_log import AuditLogViewRepo
from business_contexts.domain.entitites.audit_log import AuditLog
from messagebus.domains import Domain


async def view_audit_log(
    uow: UnitOfWork,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
) -> list[AuditLog]:
    """
    Consulta registros de auditoria com filtros opcionais.

    Se entity_type e entity_id forem informados, retorna o histórico
    completo de modificações daquela entidade específica.
    Se apenas entity_type for informado, retorna todos os registros
    daquele tipo de entidade.
    Sem filtros, retorna todos os registros de auditoria do schema.

    Args:
        uow: Unit of Work para gerenciar a sessão.
        entity_type: Tipo da entidade para filtro (opcional).
        entity_id: UUID da entidade para filtro (opcional).

    Returns:
        Lista de entidades AuditLog ordenadas da mais recente à mais antiga.
    """
    async with uow(Domain.audit_log) as uow:
        view_repo: AuditLogViewRepo = cast(AuditLogViewRepo, uow.view_repo)

        if entity_type and entity_id:
            return await view_repo.get_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
            )

        if entity_type:
            return await view_repo.get_by_entity_type(
                entity_type=entity_type,
            )

        return await view_repo.get_all()
