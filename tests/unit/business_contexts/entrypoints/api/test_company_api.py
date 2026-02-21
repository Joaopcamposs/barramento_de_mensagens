"""Testes unitários dos endpoints de Company."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.entrypoints.api import company as company_api
from business_contexts.entrypoints.schemas.company import (
    CreateCompanySchema,
    UpdateCompanySchema,
)
from tests.unit.helpers import FakeUoW


class TestCompanyApi:
    """Testes para endpoints de empresa."""

    @pytest.mark.asyncio
    async def test_company_crud_endpoints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cobre criação, atualização, consulta e remoção de empresa."""
        current = SimpleNamespace(id=uuid7.create(), company=uuid7.create())
        token = company_api.current_user.set(current)

        bus = SimpleNamespace(handle=AsyncMock(return_value=uuid7.create()))
        monkeypatch.setattr(company_api, "bootstrap", lambda **_: bus)

        body = CreateCompanySchema(
            legal_name="Acme",
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            password="secret",
            active=True,
        )
        created_id = await company_api.post_company(body)
        assert created_id is not None

        await company_api.put_company(
            "Acme", UpdateCompanySchema(new_legal_name="Acme New")
        )

        monkeypatch.setattr(company_api, "UnitOfWork", lambda **_: FakeUoW(user=current))
        monkeypatch.setattr(
            company_api, "view_company", AsyncMock(return_value=[{"id": str(created_id)}])
        )
        companies = await company_api.get_company(
            legal_name="Acme", include_deleted=False
        )
        assert companies == [{"id": str(created_id)}]

        await company_api.delete_company("Acme")
        company_api.current_user.reset(token)
