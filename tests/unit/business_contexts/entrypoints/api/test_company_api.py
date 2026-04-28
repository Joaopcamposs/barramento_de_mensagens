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


class TestCompanyApi:
    """Testes para endpoints de empresa."""

    @pytest.mark.asyncio
    async def test_company_crud_endpoints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cobre criação, atualização, consulta e remoção de empresa."""
        bus = SimpleNamespace(handle=AsyncMock(return_value=uuid7.create()), uow=object())

        body = CreateCompanySchema(
            legal_name="Acme",
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            password="Secret123",
            active=True,
        )
        created_id = await company_api.post_company(body, bus=bus)
        assert created_id is not None

        await company_api.put_company(
            "Acme", UpdateCompanySchema(new_legal_name="Acme New"), bus=bus
        )

        monkeypatch.setattr(
            company_api, "view_company", AsyncMock(return_value=[{"id": str(created_id)}])
        )
        companies = await company_api.get_company(
            legal_name="Acme", include_deleted=False, bus=bus
        )
        assert companies == [{"id": str(created_id)}]

        await company_api.delete_company("Acme", bus=bus)
