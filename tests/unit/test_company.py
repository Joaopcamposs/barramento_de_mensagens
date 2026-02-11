"""Testes unitários para o fluxo de Company."""

from uuid import UUID
import uuid7

from messagebus.entities import Aggregate, OperationType
from business_contexts.domain.aggregate.company import Company
from business_contexts.domain.commands.company import (
    CreateCompany,
    UpdateCompany,
    DeleteCompany,
)
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyUpdated,
    CompanyDeleted,
)


class TestCompanyAggregate:
    """Testes para o agregado Company."""

    def test_create_aggregate_returns_company_with_uuid(self) -> None:
        """Verifica que create_aggregate retorna uma Company com UUID válido."""
        company = Company.create_aggregate(name="Acme Corp")

        assert isinstance(company.id, UUID)
        assert company.name == "Acme Corp"

    def test_create_aggregate_generates_unique_ids(self) -> None:
        """Verifica que cada chamada gera um ID diferente."""
        company1 = Company.create_aggregate(name="Acme Corp")
        company2 = Company.create_aggregate(name="Acme Corp")

        assert company1.id != company2.id

    def test_company_inherits_from_aggregate(self) -> None:
        """Verifica que Company herda de Aggregate."""
        company = Company.create_aggregate(name="Acme Corp")

        assert isinstance(company, Aggregate)

    def test_create_sets_insert_operation_type(self) -> None:
        """Verifica que create() define o tipo de operação como INSERT."""
        company = Company.create_aggregate(name="Acme Corp")
        company.create()

        assert company._operation_type == OperationType.INSERT

    def test_create_emits_company_created_event(self) -> None:
        """Verifica que create() emite o evento CompanyCreated."""
        company = Company.create_aggregate(name="Acme Corp")
        company.create()

        assert len(company.events) == 1
        event = company.events[0]
        assert isinstance(event, CompanyCreated)
        assert event.id == company.id

    def test_update_sets_update_operation_type(self) -> None:
        """Verifica que update() define o tipo de operação como UPDATE."""
        company = Company.create_aggregate(name="Acme Corp")
        company.update(new_name="New Acme Corp")

        assert company._operation_type == OperationType.UPDATE

    def test_update_changes_name(self) -> None:
        """Verifica que update() altera o nome da empresa."""
        company = Company.create_aggregate(name="Acme Corp")
        company.update(new_name="New Acme Corp")

        assert company.name == "New Acme Corp"

    def test_update_emits_company_updated_event(self) -> None:
        """Verifica que update() emite o evento CompanyUpdated."""
        company = Company.create_aggregate(name="Acme Corp")
        company.update(new_name="New Acme Corp")

        assert len(company.events) == 1
        event = company.events[0]
        assert isinstance(event, CompanyUpdated)
        assert event.id == company.id

    def test_delete_sets_delete_operation_type(self) -> None:
        """Verifica que delete() define o tipo de operação como DELETE."""
        company = Company.create_aggregate(name="Acme Corp")
        company.delete()

        assert company._operation_type == OperationType.DELETE

    def test_delete_emits_company_deleted_event(self) -> None:
        """Verifica que delete() emite o evento CompanyDeleted."""
        company = Company.create_aggregate(name="Acme Corp")
        company.delete()

        assert len(company.events) == 1
        event = company.events[0]
        assert isinstance(event, CompanyDeleted)
        assert event.id == company.id

    def test_multiple_operations_accumulate_events(self) -> None:
        """Verifica que múltiplas operações acumulam eventos."""
        company = Company.create_aggregate(name="Acme Corp")
        company.create()
        company.update(new_name="New Acme Corp")

        assert len(company.events) == 2
        assert isinstance(company.events[0], CompanyCreated)
        assert isinstance(company.events[1], CompanyUpdated)

    def test_hash_is_based_on_id(self) -> None:
        """Verifica que o hash é baseado no ID."""
        company = Company.create_aggregate(name="Acme Corp")

        assert hash(company) == hash(company.id)


class TestCompanyCommands:
    """Testes para os comandos de Company."""

    def test_create_company_command(self) -> None:
        """Verifica a criação do comando CreateCompany."""
        command = CreateCompany(name="Acme Corp")

        assert command.name == "Acme Corp"

    def test_update_company_command(self) -> None:
        """Verifica a criação do comando UpdateCompany."""
        command = UpdateCompany(name="Acme Corp", new_name="New Acme Corp")

        assert command.name == "Acme Corp"
        assert command.new_name == "New Acme Corp"

    def test_delete_company_command(self) -> None:
        """Verifica a criação do comando DeleteCompany."""
        command = DeleteCompany(name="Acme Corp")

        assert command.name == "Acme Corp"


class TestCompanyEvents:
    """Testes para os eventos de Company."""

    def test_company_created_event(self) -> None:
        """Verifica a criação do evento CompanyCreated."""
        uid = uuid7.create()
        event = CompanyCreated(id=uid)

        assert event.id == uid

    def test_company_updated_event(self) -> None:
        """Verifica a criação do evento CompanyUpdated."""
        uid = uuid7.create()
        event = CompanyUpdated(id=uid)

        assert event.id == uid

    def test_company_deleted_event(self) -> None:
        """Verifica a criação do evento CompanyDeleted."""
        uid = uuid7.create()
        event = CompanyDeleted(id=uid)

        assert event.id == uid
