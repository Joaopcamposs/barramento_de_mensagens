"""Testes de integração para o fluxo de Company."""

from uuid import UUID

import pytest

from messagebus.bootstrap import bootstrap
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.views.company import view_company
from business_contexts.domain.commands.company import (
    CreateCompany,
    UpdateCompany,
    DeleteCompany,
)
from business_contexts.domain.excecoes import (
    CompanyAlreadyRegistered,
    CompanyNotFound,
)


class TestCreateCompany:
    """Testes de integração para criação de empresa."""

    async def test_create_company_returns_uuid(self, engine) -> None:
        """Verifica que criar uma empresa retorna um UUID válido."""
        bus = bootstrap(raise_event_errors=True)
        command = CreateCompany(name="Integration Corp")

        result = await bus.handle(command)

        assert isinstance(result, UUID)

    async def test_create_company_persists_in_database(self, engine) -> None:
        """Verifica que a empresa é persistida no banco de dados."""
        bus = bootstrap(raise_event_errors=True)
        command = CreateCompany(name="Persisted Corp")
        await bus.handle(command)

        uow = UnitOfWork()
        companies = await view_company(uow, "Persisted Corp")

        assert len(companies) == 1
        assert companies[0].name == "Persisted Corp"
        assert isinstance(companies[0].id, UUID)

    async def test_create_duplicate_company_raises_error(self, engine) -> None:
        """Verifica que criar empresa com nome duplicado lança exceção."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Unique Corp"))

        bus2 = bootstrap(raise_event_errors=True)
        with pytest.raises(CompanyAlreadyRegistered):
            await bus2.handle(CreateCompany(name="Unique Corp"))


class TestUpdateCompany:
    """Testes de integração para atualização de empresa."""

    async def test_update_company_changes_name(self, engine) -> None:
        """Verifica que a atualização altera o nome da empresa."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Old Name"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(UpdateCompany(name="Old Name", new_name="New Name"))

        uow = UnitOfWork()
        companies = await view_company(uow, "New Name")

        assert len(companies) == 1
        assert companies[0].name == "New Name"

    async def test_update_company_old_name_not_found(self, engine) -> None:
        """Verifica que o nome antigo não existe mais após atualização."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Before Update"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(UpdateCompany(name="Before Update", new_name="After Update"))

        uow = UnitOfWork()
        companies = await view_company(uow, "Before Update")

        assert companies == []

    async def test_update_nonexistent_company_raises_error(self, engine) -> None:
        """Verifica que atualizar empresa inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(CompanyNotFound):
            await bus.handle(UpdateCompany(name="Ghost Corp", new_name="New Ghost"))


class TestDeleteCompany:
    """Testes de integração para exclusão de empresa."""

    async def test_delete_company_removes_from_database(self, engine) -> None:
        """Verifica que a exclusão remove a empresa do banco."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="To Delete"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteCompany(name="To Delete"))

        uow = UnitOfWork()
        companies = await view_company(uow, "To Delete")

        assert companies == []

    async def test_delete_nonexistent_company_raises_error(self, engine) -> None:
        """Verifica que excluir empresa inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(CompanyNotFound):
            await bus.handle(DeleteCompany(name="Nonexistent Corp"))


class TestViewCompany:
    """Testes de integração para consulta de empresa."""

    async def test_view_existing_company_by_name(self, engine) -> None:
        """Verifica que consultar empresa existente por nome retorna dados corretos."""
        bus = bootstrap(raise_event_errors=True)
        company_id = await bus.handle(CreateCompany(name="Viewable Corp"))

        uow = UnitOfWork()
        companies = await view_company(uow, "Viewable Corp")

        assert len(companies) == 1
        assert companies[0].id == company_id
        assert companies[0].name == "Viewable Corp"

    async def test_view_nonexistent_company_returns_empty_list(self, engine) -> None:
        """Verifica que consultar empresa inexistente retorna lista vazia."""
        uow = UnitOfWork()
        companies = await view_company(uow, "Does Not Exist")

        assert companies == []

    async def test_view_all_companies(self, engine) -> None:
        """Verifica que consultar sem filtro retorna todas as empresas."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Company A"))
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(CreateCompany(name="Company B"))

        uow = UnitOfWork()
        companies = await view_company(uow)

        assert len(companies) == 2
        names = {c.name for c in companies}
        assert names == {"Company A", "Company B"}

    async def test_view_all_companies_empty_database(self, engine) -> None:
        """Verifica que consultar sem filtro em banco vazio retorna lista vazia."""
        uow = UnitOfWork()
        companies = await view_company(uow)

        assert companies == []
