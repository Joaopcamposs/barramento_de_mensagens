"""Mapeamento ORM da tabela company."""

from sqlalchemy import Table, Column, String, UUID, Boolean, Index, text

from business_contexts.domain.aggregate.company import Company
from infra.database import mapper_registry

company = Table(
    "company",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(255), nullable=False, index=True),
    Column("deleted", Boolean, nullable=False, default=False),
    Index('ix_company_name_deleted', 'name', unique=True, postgresql_where=text('deleted = false')),
)

company_mapper = mapper_registry.map_imperatively(Company, company)
