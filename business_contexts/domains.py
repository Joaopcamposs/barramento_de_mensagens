"""Módulo de mapeamento de domínios para seus respectivos repositórios."""

from enum import Enum

from business_contexts.adapters.repository.domain_repo.audit_log import (
    AuditLogDomainRepo,
)
from business_contexts.adapters.repository.domain_repo.company import (
    CompanyDomainRepo,
)
from business_contexts.adapters.repository.domain_repo.user import UserDomainRepo
from business_contexts.adapters.repository.view_repo.audit_log import (
    AuditLogViewRepo,
)
from business_contexts.adapters.repository.view_repo.company import (
    CompanyViewRepo,
)
from business_contexts.adapters.repository.view_repo.user import (
    UserViewRepo,
)


class Domain(Enum):
    """Enum que mapeia domínios para seus repositórios (escrita, leitura)."""

    user = (UserDomainRepo, UserViewRepo)
    company = (CompanyDomainRepo, CompanyViewRepo)
    audit_log = (AuditLogDomainRepo, AuditLogViewRepo)
