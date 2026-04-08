"""baseline schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from libs.utils import is_public_schema

revision: str = "101e3e6aef01"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def _upgrade_public() -> None:
    """Cria tabelas compartilhadas no schema public."""
    op.create_table(
        "public_user",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company", sa.UUID(), nullable=False),
        sa.Column("email_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("email_lookup_hmac", sa.String(length=64), nullable=False),
        sa.Column("cpf_lookup_hmac", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_public_user_email_lookup_company",
        "public_user",
        ["email_lookup_hmac", "company"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_public_user_cpf_lookup_company",
        "public_user",
        ["cpf_lookup_hmac", "company"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_public_user_email_lookup_hmac",
        "public_user",
        ["email_lookup_hmac"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_public_user_cpf_lookup_hmac",
        "public_user",
        ["cpf_lookup_hmac"],
        unique=True,
        schema="public",
    )


def _upgrade_tenant(schema: str) -> None:
    """Cria tabelas de tenant no schema informado."""
    op.create_table(
        "company",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column("responsible_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("cpf", sa.String(length=14), nullable=False),
        sa.Column("cnpj", sa.String(length=18), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index(
        "ix_company_legal_name_not_deleted",
        "company",
        ["legal_name"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_company_legal_name", "company", ["legal_name"], schema=schema)

    op.create_table(
        "user",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("admin", sa.Boolean(), nullable=False),
        sa.Column("company", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company"], [f"{schema}.company.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index(
        "ix_user_email_not_deleted",
        "user",
        ["email"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("old_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"], schema=schema)
    op.create_index(
        "ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"], schema=schema
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"], schema=schema)


def _downgrade_public() -> None:
    """Remove tabelas compartilhadas do schema public."""
    op.drop_index(
        "ix_public_user_cpf_lookup_hmac", table_name="public_user", schema="public"
    )
    op.drop_index(
        "ix_public_user_email_lookup_hmac", table_name="public_user", schema="public"
    )
    op.drop_index(
        "ix_public_user_cpf_lookup_company", table_name="public_user", schema="public"
    )
    op.drop_index(
        "ix_public_user_email_lookup_company", table_name="public_user", schema="public"
    )
    op.drop_table("public_user", schema="public")


def _downgrade_tenant(schema: str) -> None:
    """Remove tabelas de tenant do schema informado."""
    op.drop_index("ix_audit_log_user_id", table_name="audit_log", schema=schema)
    op.drop_index("ix_audit_log_entity", table_name="audit_log", schema=schema)
    op.drop_index("ix_audit_log_created_at", table_name="audit_log", schema=schema)
    op.drop_table("audit_log", schema=schema)
    op.drop_index("ix_user_email_not_deleted", table_name="user", schema=schema)
    op.drop_table("user", schema=schema)
    op.drop_index("ix_company_legal_name", table_name="company", schema=schema)
    op.drop_index(
        "ix_company_legal_name_not_deleted", table_name="company", schema=schema
    )
    op.drop_table("company", schema=schema)


def upgrade(schema: str) -> None:
    """Executa upgrade para o schema informado."""
    if is_public_schema(schema):
        _upgrade_public()
        return

    _upgrade_tenant(schema)


def downgrade(schema: str) -> None:
    """Executa downgrade para o schema informado."""
    if is_public_schema(schema):
        _downgrade_public()
        return

    _downgrade_tenant(schema)
