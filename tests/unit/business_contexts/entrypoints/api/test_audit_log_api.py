"""Testes unitários do endpoint de AuditLog."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.domain.value_objects.enums import EntityType
from business_contexts.entrypoints.api import audit_log as audit_api
from business_contexts.entrypoints.schemas.audit_log import ReadAuditLogSchema
from tests.unit.helpers import FakeUoW


class TestAuditApi:
    """Testes para endpoint de auditoria."""

    @pytest.mark.asyncio
    async def test_get_audit_logs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Retorna lista de logs de auditoria com filtros opcionais."""
        current = SimpleNamespace(id=uuid7.create(), company=uuid7.create())
        token = audit_api.current_user.set(current)

        monkeypatch.setattr(audit_api, "UnitOfWork", lambda **_: FakeUoW(user=current))
        monkeypatch.setattr(
            audit_api,
            "view_audit_log",
            AsyncMock(
                return_value=[
                    ReadAuditLogSchema(
                        id=uuid7.create(),
                        entity_type="User",
                        entity_id=uuid7.create(),
                        operation="UPDATE",
                        old_data={"a": 1},
                        new_data={"a": 2},
                        user_id=current.id,
                        created_at=datetime.now(timezone.utc),
                    )
                ]
            ),
        )

        response = await audit_api.get_audit_logs(
            entity_type=EntityType.USER, entity_id=uuid7.create()
        )
        assert len(response) == 1

        audit_api.current_user.reset(token)
