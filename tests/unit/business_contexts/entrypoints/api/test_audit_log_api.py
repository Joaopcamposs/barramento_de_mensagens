"""Testes unitários do endpoint de AuditLog."""

from datetime import datetime, timezone
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
        user_id = uuid7.create()
        bus = type("FakeBus", (), {"uow": FakeUoW()})()
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
                        user_id=user_id,
                        created_at=datetime.now(timezone.utc),
                    )
                ]
            ),
        )

        response = await audit_api.get_audit_logs(
            bus=bus,
            entity_type=EntityType.USER,
            entity_id=uuid7.create(),
        )
        assert len(response) == 1
