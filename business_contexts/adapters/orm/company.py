"""Mapeamento ORM da tabela company."""

from sqlalchemy import Table, Column, String, UUID

from business_contexts.domain.aggregate.company import Company
from infra.database import mapper_registry

company = Table(
    "company",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(255), nullable=False, unique=True, index=True),
)

company_mapper = mapper_registry.map_imperatively(Company, company)
