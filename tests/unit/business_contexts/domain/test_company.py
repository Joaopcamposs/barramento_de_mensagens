"""Testes unitários para o fluxo de Company."""

from uuid import UUID

import uuid7

from business_contexts.domain.aggregate.company import Company
from business_contexts.domain.commands.company import (
    CreateCompany,
    DeleteCompany,
    UpdateCompany,
)
from business_contexts.domain.entitites.company import Company as CompanyEntity
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyDeleted,
    CompanyUpdated,
)
from business_contexts.domain.events.user import (
    TimeToCreateCompanyAdminUser,
    TimeToCreateInitialCompanyUser,
)
from business_contexts.entrypoints.schemas.company import (
    CreateCompanySchema,
    ReadCompanySchema,
    UpdateCompanySchema,
)
from messagebus.entities import Aggregate, OperationType


def _make_company(**overrides) -> Company:
    """Função auxiliar para criar um agregado Company com valores padrão."""
    defaults = dict(
        legal_name="Acme Corp",
        trade_name="Acme",
        responsible_name="John Doe",
        email="contact@acme.com",
        cpf="12345678901",
        cnpj="12345678000190",
        active=True,
    )
    defaults.update(overrides)
    return Company.create_aggregate(**defaults)


class TestCompanyAggregate:
    """Testes para o agregado Company."""

    def test_create_aggregate_returns_company_with_uuid(self) -> None:
        """Verifica que create_aggregate retorna uma Company com UUID válido."""
        company = _make_company()

        assert isinstance(company.id, UUID)
        assert company.legal_name == "Acme Corp"
        assert company.trade_name == "Acme"
        assert company.responsible_name == "John Doe"
        assert company.email == "contact@acme.com"
        assert company.cpf == "12345678901"
        assert company.cnpj == "12345678000190"
        assert company.active is True
        assert company.deleted_at is None

    def test_create_aggregate_generates_unique_ids(self) -> None:
        """Verifica que cada chamada gera um ID diferente."""
        company1 = _make_company()
        company2 = _make_company()

        assert company1.id != company2.id

    def test_create_aggregate_with_optional_fields_none(self) -> None:
        """Verifica que campos opcionais podem ser None."""
        company = _make_company(trade_name=None, cnpj=None)

        assert company.trade_name is None
        assert company.cnpj is None

    def test_company_inherits_from_aggregate(self) -> None:
        """Verifica que Company herda de Aggregate."""
        company = _make_company()

        assert isinstance(company, Aggregate)

    def test_create_sets_insert_operation_type(self) -> None:
        """Verifica que create() define o tipo de operação como INSERT."""
        company = _make_company()
        company.create(password="secret123")

        assert company._operation_type == OperationType.INSERT

    def test_create_emits_company_created_event(self) -> None:
        """Verifica que create() emite o evento CompanyCreated."""
        company = _make_company()
        company.create(password="secret123")

        created_events = [e for e in company.events if isinstance(e, CompanyCreated)]
        assert len(created_events) == 1
        assert created_events[0].id == company.id

    def test_create_emits_time_to_create_initial_user_event(self) -> None:
        """Verifica que create() emite evento para criar usuário inicial."""
        company = _make_company()
        company.create(password="secret123")

        user_events = [
            e for e in company.events if isinstance(e, TimeToCreateInitialCompanyUser)
        ]
        assert len(user_events) == 1
        event = user_events[0]
        assert event.company == company.id
        assert event.name == company.responsible_name
        assert event.email == company.email
        assert event.password == "secret123"

    def test_create_emits_admin_user_event_when_not_first_company(self) -> None:
        """Verifica que create() emite evento de usuário admin quando não é a primeira empresa."""
        company = _make_company()  # _first_company_id=None por padrão
        company.create(password="secret123")

        admin_events = [
            e for e in company.events if isinstance(e, TimeToCreateCompanyAdminUser)
        ]
        assert len(admin_events) == 1
        assert admin_events[0].company == company.id

    def test_create_does_not_emit_admin_user_event_for_first_company(self) -> None:
        """Verifica que create() NÃO emite evento de admin quando é a primeira empresa."""
        first_id = uuid7.create()
        company = _make_company(_first_company_id=first_id)
        company.create(password="secret123")

        admin_events = [
            e for e in company.events if isinstance(e, TimeToCreateCompanyAdminUser)
        ]
        assert len(admin_events) == 0

    def test_update_sets_update_operation_type(self) -> None:
        """Verifica que update() define o tipo de operação como UPDATE."""
        company = _make_company()
        company.update(legal_name="New Acme Corp")

        assert company._operation_type == OperationType.UPDATE

    def test_update_changes_legal_name(self) -> None:
        """Verifica que update() altera a razão social da empresa."""
        company = _make_company()
        company.update(legal_name="New Acme Corp")

        assert company.legal_name == "New Acme Corp"

    def test_update_changes_trade_name(self) -> None:
        """Verifica que update() altera o nome fantasia da empresa."""
        company = _make_company()
        company.update(trade_name="New Acme")

        assert company.trade_name == "New Acme"

    def test_update_changes_responsible_name(self) -> None:
        """Verifica que update() altera o nome do responsável."""
        company = _make_company()
        company.update(responsible_name="Jane Doe")

        assert company.responsible_name == "Jane Doe"

    def test_update_changes_email(self) -> None:
        """Verifica que update() altera o email da empresa."""
        company = _make_company()
        company.update(email="new@acme.com")

        assert company.email == "new@acme.com"

    def test_update_changes_active(self) -> None:
        """Verifica que update() altera o status de ativação."""
        company = _make_company(active=True)
        company.update(active=False)

        assert company.active is False

    def test_update_with_none_does_not_change_fields(self) -> None:
        """Verifica que update() com None não altera os campos."""
        company = _make_company()
        original_name = company.legal_name
        original_email = company.email
        company.update(legal_name=None, email=None)

        assert company.legal_name == original_name
        assert company.email == original_email

    def test_update_emits_company_updated_event(self) -> None:
        """Verifica que update() emite o evento CompanyUpdated."""
        company = _make_company()
        company.update(legal_name="New Acme Corp")

        assert len(company.events) == 1
        event = company.events[0]
        assert isinstance(event, CompanyUpdated)
        assert event.id == company.id

    def test_delete_sets_delete_operation_type(self) -> None:
        """Verifica que delete() define o tipo de operação como DELETE (soft delete)."""
        company = _make_company()
        company.delete()

        assert company._operation_type == OperationType.DELETE
        assert company.is_deleted is True

    def test_delete_emits_company_deleted_event(self) -> None:
        """Verifica que delete() emite o evento CompanyDeleted."""
        company = _make_company()
        company.delete()

        assert len(company.events) == 1
        event = company.events[0]
        assert isinstance(event, CompanyDeleted)
        assert event.id == company.id

    def test_multiple_operations_accumulate_events(self) -> None:
        """Verifica que múltiplas operações acumulam eventos."""
        company = _make_company()
        company.create(password="secret123")
        company.update(legal_name="New Acme Corp")

        created_events = [e for e in company.events if isinstance(e, CompanyCreated)]
        updated_events = [e for e in company.events if isinstance(e, CompanyUpdated)]
        assert len(created_events) == 1
        assert len(updated_events) == 1

    def test_hash_is_based_on_id(self) -> None:
        """Verifica que o hash é baseado no ID."""
        company = _make_company()

        assert hash(company) == hash(company.id)


class TestCompanyCommands:
    """Testes para os comandos de Company."""

    def test_create_company_command(self) -> None:
        """Verifica a criação do comando CreateCompany com todos os campos."""
        command = CreateCompany(
            legal_name="Acme Corp",
            responsible_name="John Doe",
            active=True,
            cpf="12345678901",
            email="contact@acme.com",
            password="secret123",
            cnpj="12345678000190",
            trade_name="Acme",
        )

        assert command.legal_name == "Acme Corp"
        assert command.responsible_name == "John Doe"
        assert command.active is True
        assert command.cpf == "12345678901"
        assert command.email == "contact@acme.com"
        assert command.password == "secret123"
        assert command.cnpj == "12345678000190"
        assert command.trade_name == "Acme"
        assert command.should_create_user is True
        assert command._first_company_id is None

    def test_create_company_command_optional_fields(self) -> None:
        """Verifica que campos opcionais do CreateCompany são None por padrão."""
        command = CreateCompany(
            legal_name="Acme",
            responsible_name="John",
            active=True,
            cpf="12345678901",
            email="a@b.com",
            password="pwd",
        )

        assert command.trade_name is None
        assert command.cnpj is None

    def test_update_company_command(self) -> None:
        """Verifica a criação do comando UpdateCompany."""
        command = UpdateCompany(
            legal_name="Acme Corp",
            new_legal_name="New Acme Corp",
            new_trade_name="New Acme",
            new_responsible_name="Jane Doe",
            new_email="new@acme.com",
            new_active=False,
        )

        assert command.legal_name == "Acme Corp"
        assert command.new_legal_name == "New Acme Corp"
        assert command.new_trade_name == "New Acme"
        assert command.new_responsible_name == "Jane Doe"
        assert command.new_email == "new@acme.com"
        assert command.new_active is False

    def test_update_company_command_optional_fields(self) -> None:
        """Verifica que campos opcionais do UpdateCompany são None por padrão."""
        command = UpdateCompany(legal_name="Acme Corp")

        assert command.new_legal_name is None
        assert command.new_trade_name is None
        assert command.new_responsible_name is None
        assert command.new_email is None
        assert command.new_active is None

    def test_delete_company_command(self) -> None:
        """Verifica a criação do comando DeleteCompany."""
        command = DeleteCompany(legal_name="Acme Corp")

        assert command.legal_name == "Acme Corp"


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


class TestCompanyEntity:
    """Testes para a entidade de leitura Company."""

    def test_company_entity_creation(self) -> None:
        """Verifica a criação da entidade Company com todos os campos."""
        uid = uuid7.create()
        entity = CompanyEntity(
            id=uid,
            legal_name="Acme Corp",
            trade_name="Acme",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            cnpj="12345678000190",
            active=True,
        )

        assert entity.id == uid
        assert entity.legal_name == "Acme Corp"
        assert entity.trade_name == "Acme"
        assert entity.responsible_name == "John Doe"
        assert entity.email == "contact@acme.com"
        assert entity.cpf == "12345678901"
        assert entity.cnpj == "12345678000190"
        assert entity.active is True
        assert entity.deleted_at is None

    def test_company_entity_optional_fields(self) -> None:
        """Verifica que campos opcionais da entidade podem ser None."""
        uid = uuid7.create()
        entity = CompanyEntity(
            id=uid,
            legal_name="Acme Corp",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            active=True,
        )

        assert entity.trade_name is None
        assert entity.cnpj is None

    def test_company_entity_is_frozen(self) -> None:
        """Verifica que a entidade Company é imutável (frozen dataclass)."""
        uid = uuid7.create()
        entity = CompanyEntity(
            id=uid,
            legal_name="Acme Corp",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            active=True,
        )

        import pytest

        with pytest.raises(AttributeError):
            setattr(entity, "legal_name", "New Name")


class TestCompanySchemas:
    """Testes para os schemas de Company."""

    def test_create_company_schema(self) -> None:
        """Verifica o schema de criação de empresa."""
        schema = CreateCompanySchema(
            legal_name="Acme Corp",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            password="Secret123",
        )

        assert schema.legal_name == "Acme Corp"
        assert schema.active is True
        assert schema.trade_name is None
        assert schema.cnpj is None

    def test_create_company_schema_rejects_weak_password(self) -> None:
        """Rejeita senha de cadastro sem complexidade mínima."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateCompanySchema(
                legal_name="Acme Corp",
                responsible_name="John Doe",
                email="contact@acme.com",
                cpf="12345678901",
                password="secret123",
            )

    def test_update_company_schema(self) -> None:
        """Verifica o schema de atualização de empresa."""
        schema = UpdateCompanySchema(
            new_legal_name="New Acme",
        )

        assert schema.new_legal_name == "New Acme"
        assert schema.new_legal_name == "New Acme"
        assert schema.new_trade_name is None
        assert schema.new_responsible_name is None
        assert schema.new_email is None
        assert schema.new_active is None

    def test_read_company_schema(self) -> None:
        """Verifica o schema de leitura de empresa."""
        uid = uuid7.create()
        schema = ReadCompanySchema(
            id=uid,
            legal_name="Acme Corp",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            active=True,
        )

        assert schema.id == uid
        assert schema.legal_name == "Acme Corp"
        assert schema.trade_name is None
        assert schema.cnpj is None
