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
        assert companies[0].deleted is False
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
    """Testes de integração para exclusão (soft delete) de empresa."""

    async def test_delete_company_soft_deletes_from_database(self, engine) -> None:
        """Verifica que a exclusão marca a empresa como deletada (soft delete)."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="To Delete"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteCompany(name="To Delete"))

        uow = UnitOfWork()
        companies = await view_company(uow, "To Delete")
        assert companies == []

    async def test_deleted_company_visible_with_include_deleted(self, engine) -> None:
        """Verifica que empresa deletada é visível com include_deleted=True."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Soft Deleted"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteCompany(name="Soft Deleted"))

        uow = UnitOfWork()
        companies = await view_company(uow, "Soft Deleted", include_deleted=True)

        assert len(companies) == 1
        assert companies[0].name == "Soft Deleted"
        assert companies[0].deleted is True

    async def test_delete_nonexistent_company_raises_error(self, engine) -> None:
        """Verifica que excluir empresa inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(CompanyNotFound):
            await bus.handle(DeleteCompany(name="Nonexistent Corp"))

    async def test_can_recreate_company_after_soft_delete(self, engine) -> None:
        """Verifica que é possível recriar empresa com mesmo nome após soft delete."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Recyclable Corp"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteCompany(name="Recyclable Corp"))

        bus3 = bootstrap(raise_event_errors=True)
        new_id = await bus3.handle(CreateCompany(name="Recyclable Corp"))

        assert isinstance(new_id, UUID)


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
        assert companies[0].deleted is False

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

    async def test_view_all_companies_excludes_deleted(self, engine) -> None:
        """Verifica que consultar sem include_deleted exclui empresas deletadas."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Active Corp"))
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(CreateCompany(name="Deleted Corp"))

        bus3 = bootstrap(raise_event_errors=True)
        await bus3.handle(DeleteCompany(name="Deleted Corp"))

        uow = UnitOfWork()
        companies = await view_company(uow)

        assert len(companies) == 1
        assert companies[0].name == "Active Corp"

    async def test_view_all_companies_includes_deleted(self, engine) -> None:
        """Verifica que consultar com include_deleted=True retorna todas."""
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(CreateCompany(name="Active Corp 2"))
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(CreateCompany(name="Deleted Corp 2"))

        bus3 = bootstrap(raise_event_errors=True)
        await bus3.handle(DeleteCompany(name="Deleted Corp 2"))

        uow = UnitOfWork()
        companies = await view_company(uow, include_deleted=True)

        assert len(companies) == 2
        names = {c.name for c in companies}
        assert names == {"Active Corp 2", "Deleted Corp 2"}
