"""Mapeamento ORM da tabela user."""

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Table,
    text,
)

from business_contexts.domain.aggregate.user import PublicUser, User
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

public_user = Table(
    "public_user",
    mapper_registry.metadata,
    Column("id", UUID, primary_key=True),
    Column("company", UUID, nullable=False),
    Column("email_encrypted", LargeBinary, nullable=False),
    Column("email_hash", String(64), nullable=False),
    Column("password_hash", String(128), nullable=False),
    Column("active", Boolean, nullable=False),
    Column("deleted", Boolean, nullable=False, default=False),
    Index(
        "ix_public_user_email_deleted",
        "email_hash",
        unique=True,
        postgresql_where=text("deleted = false"),
    ),
    Index("ix_public_user_email_hash_company", "email_hash", "company"),
    schema="public",
)
public_user_mapper = mapper_registry.map_imperatively(PublicUser, public_user)
