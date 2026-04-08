"""${message}."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
from libs.utils import is_public_schema

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | None = ${repr(branch_labels)}
depends_on: str | None = ${repr(depends_on)}


def _upgrade_public() -> None:
    """Operacoes de upgrade no schema public."""
    pass


def _upgrade_tenant(schema: str) -> None:
    """Operacoes de upgrade em schemas tenant."""
    pass


def _downgrade_public() -> None:
    """Operacoes de downgrade no schema public."""
    pass


def _downgrade_tenant(schema: str) -> None:
    """Operacoes de downgrade em schemas tenant."""
    pass


def upgrade(schema: str) -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}
    if is_public_schema(schema):
        _upgrade_public()
        return

    _upgrade_tenant(schema)


def downgrade(schema: str) -> None:
    """Downgrade schema."""
    ${upgrades if upgrades else "pass"}
    if is_public_schema(schema):
        _downgrade_public()
        return

    _downgrade_tenant(schema)
