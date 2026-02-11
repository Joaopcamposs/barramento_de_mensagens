"""Mapeamento ORM da tabela user."""

from sqlalchemy import Table, Column, String, UUID, ForeignKey, Boolean, Index, text

from business_contexts.domain.aggregate.user import User
from infra.database import mapper_registry

user = Table(
    "user",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("email", String(255), nullable=False),
    Column("password", String, nullable=False),
    Column("cpf", String(11), nullable=False),
    Column("active", Boolean, nullable=False),
    Column("admin", Boolean, nullable=False),
    Column("company", UUID, ForeignKey("company.id"), nullable=False),
    Column("deleted", Boolean, nullable=False, default=False),
    Index(
        "ix_user_email_deleted",
        "email",
        unique=True,
        postgresql_where=text("deleted = false"),
    ),
)

user_mapper = mapper_registry.map_imperatively(User, user)
