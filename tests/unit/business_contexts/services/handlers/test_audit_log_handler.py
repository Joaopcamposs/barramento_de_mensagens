"""Testes unitários dos handlers de auditoria."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.domain.value_objects.enums import AuditOperation
from business_contexts.services.handlers import audit_log as audit_log_handlers
from tests.unit.helpers import FakeUoW


class TestAuditLogHandlers:
    """Testes para handlers de auditoria."""

    @pytest.mark.asyncio
    async def test_persist_audit_log_returns_none_for_non_auditable_event(self) -> None:
        """Ignora eventos sem metadados auditáveis."""

        @dataclass(kw_only=True)
        class PlainEvent:
            id: Any

        result = await audit_log_handlers._persist_audit_log(  # noqa: SLF001
            PlainEvent(id=uuid7.create()),
            AuditOperation.CREATE,
            FakeUoW(),  # type: ignore[arg-type]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_persist_audit_log_success_and_wrapper_functions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Persiste auditoria e cobre wrappers de create/update/delete."""

        @dataclass(kw_only=True)
        class DemoEvent(audit_log_handlers.Event, audit_log_handlers.AuditableEvent):
            id: Any

        event = DemoEvent(
            id=uuid7.create(), entity_type="User", old_data={"a": 1}, new_data={"a": 2}
        )
        audit = SimpleNamespace(id=uuid7.create())

        domain_repo = SimpleNamespace(create_from_event=AsyncMock(return_value=audit))
        uow = FakeUoW(domain_repo=domain_repo, user=SimpleNamespace(id=uuid7.create()))

        persisted = await audit_log_handlers._persist_audit_log(
            event, AuditOperation.UPDATE, uow
        )  # noqa: SLF001
        assert persisted is audit
        domain_repo.create_from_event.assert_awaited_once()
        assert uow.committed is True

        calls: list[AuditOperation] = []

        async def fake_persist(event: Any, operation: AuditOperation, uow: Any) -> None:
            calls.append(operation)

        monkeypatch.setattr(audit_log_handlers, "_persist_audit_log", fake_persist)

        await audit_log_handlers.audit_entity_created(event, uow)  # type: ignore[arg-type]
        await audit_log_handlers.audit_entity_updated(event, uow)  # type: ignore[arg-type]
        await audit_log_handlers.audit_entity_deleted(event, uow)  # type: ignore[arg-type]

        assert calls == [
            AuditOperation.CREATE,
            AuditOperation.UPDATE,
            AuditOperation.DELETE,
        ]
