"""Mapeamento ORM da tabela user."""

from sqlalchemy import Table, Column, String, UUID, ForeignKey

from business_contexts.domain.aggregate.user import User
from infra.database import mapper_registry

user = Table(
    "user",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("email", String(255), nullable=False),
    Column("password", String, nullable=False),
    Column("company", UUID, ForeignKey("company.id"), nullable=False),
)

user_mapper = mapper_registry.map_imperatively(User, user)
