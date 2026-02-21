"""Testes unitários dos handlers de Company."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.domain.commands.company import (
    CreateCompany,
    DeleteCompany,
    UpdateCompany,
)
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyDeleted,
    CompanyUpdated,
)
from business_contexts.services.handlers import company as company_handlers
from tests.unit.helpers import FakeUoW


class TestCompanyHandlers:
    """Testes dos handlers do domínio Company."""

    @pytest.mark.asyncio
    async def test_create_company_success(self) -> None:
        """Cria empresa e confirma persistência/commit no fluxo feliz."""
        company_id = uuid7.create()
        company = SimpleNamespace(id=company_id, create=lambda **_: None)
        domain_repo = SimpleNamespace(
            create_aggregate=AsyncMock(return_value=company), add=AsyncMock()
        )
        uow = FakeUoW(domain_repo=domain_repo, user=SimpleNamespace(id=uuid7.create()))

        command = CreateCompany(
            legal_name="Acme",
            responsible_name="John",
            active=True,
            cpf="12345678901",
            email="john@example.com",
            password="secret",
        )

        result = await company_handlers.create_company(command, uow)  # type: ignore[arg-type]

        assert result == company_id
        domain_repo.create_aggregate.assert_awaited_once()
        domain_repo.add.assert_awaited_once_with(company)
        assert uow.committed is True

    @pytest.mark.asyncio
    async def test_create_company_rolls_back_schema_on_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deleta schema quando ocorre erro durante criação da empresa."""
        domain_repo = SimpleNamespace(
            create_aggregate=AsyncMock(side_effect=RuntimeError("fail"))
        )
        uow = FakeUoW(domain_repo=domain_repo)
        delete_calls: list[str] = []

        async def fake_delete_schema(schema: str) -> None:
            delete_calls.append(schema)

        monkeypatch.setattr(company_handlers, "delete_schema", fake_delete_schema)

        command = CreateCompany(
            legal_name="Acme",
            responsible_name="John",
            active=True,
            cpf="12345678901",
            email="john@example.com",
            password="secret",
        )

        with pytest.raises(RuntimeError, match="fail"):
            await company_handlers.create_company(command, uow)  # type: ignore[arg-type]

        assert delete_calls == ["Acme"]

    @pytest.mark.asyncio
    async def test_update_and_delete_company(self) -> None:
        """Atualiza e remove empresa chamando os métodos esperados."""
        company = SimpleNamespace(update=AsyncMock(), delete=AsyncMock())
        domain_repo = SimpleNamespace(
            get_by_legal_name=AsyncMock(return_value=company),
            add=AsyncMock(),
            remove=AsyncMock(),
        )
        uow = FakeUoW(domain_repo=domain_repo, user=SimpleNamespace(id=uuid7.create()))

        await company_handlers.update_company(
            UpdateCompany(legal_name="Acme", new_legal_name="Acme 2"), uow
        )  # type: ignore[arg-type]
        await company_handlers.delete_company(DeleteCompany(legal_name="Acme"), uow)  # type: ignore[arg-type]

        assert domain_repo.get_by_legal_name.await_count == 2
        domain_repo.add.assert_awaited_once()
        domain_repo.remove.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_company_event_handlers_log(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Registra logs ao receber eventos de empresa."""
        logs: list[str] = []
        monkeypatch.setattr(
            company_handlers.logger, "info", lambda message: logs.append(message)
        )

        event = CompanyCreated(id=uuid7.create(), entity_type="Company")
        await company_handlers.company_created(event, FakeUoW())  # type: ignore[arg-type]
        await company_handlers.company_updated(
            CompanyUpdated(id=event.id, entity_type="Company"), FakeUoW()
        )  # type: ignore[arg-type]
        await company_handlers.company_deleted(
            CompanyDeleted(id=event.id, entity_type="Company"), FakeUoW()
        )  # type: ignore[arg-type]

        assert len(logs) == 3
