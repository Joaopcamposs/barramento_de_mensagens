"""Mapeamento ORM da tabela company."""

from sqlalchemy import Table, Column, String, UUID, Boolean, Index, text

from business_contexts.domain.aggregate.company import Company
from infra.database import mapper_registry

company = Table(
    "company",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("legal_name", String(255), nullable=False, index=True),
    Column("trade_name", String(255), nullable=True),
    Column("responsible_name", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("cpf", String(14), nullable=False),
    Column("cnpj", String(18), nullable=True),
    Column("active", Boolean, nullable=False, default=True),
    Column("deleted", Boolean, nullable=False, default=False),
    Index(
        "ix_company_legal_name_deleted",
        "legal_name",
        unique=True,
        postgresql_where=text("deleted = false"),
    ),
)

company_mapper = mapper_registry.map_imperatively(Company, company)
