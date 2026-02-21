"""Mapeamento ORM da tabela company."""

from sqlalchemy import UUID, Boolean, Column, DateTime, Index, String, Table, text

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
    Column("created_at", DateTime(timezone=True), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    Column("updated_by", UUID, nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Column("deleted_by", UUID, nullable=True),
    Index(
        "ix_company_legal_name_not_deleted",
        "legal_name",
        unique=True,
        postgresql_where=text("deleted_at IS NULL"),
    ),
)

company_mapper = mapper_registry.map_imperatively(Company, company)
