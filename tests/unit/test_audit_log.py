"""Testes unitários para o sistema de auditoria."""

from datetime import datetime, timezone
from uuid import UUID

import pytest
import uuid7

from messagebus.entities import AuditableEvent
from messagebus.messagebus import Event
from business_contexts.domain.entitites.audit_log import AuditLog as AuditLogRead
from business_contexts.domain.value_objects.enums import (
    AuditConstant,
    AuditOperation,
    EntityType,
)

_TEST_COMPANY_ID = uuid7.create()
_TEST_USER_ID = uuid7.create()


class TestAuditableEvent:
    """Testes para o mixin AuditableEvent."""

    def test_auditable_event_default_values(self) -> None:
        event = AuditableEvent()
        assert event.entity_type == ""
        assert event.old_data is None
        assert event.new_data is None

    def test_auditable_event_with_data(self) -> None:
        event = AuditableEvent(
            entity_type="TestEntity", old_data={"a": 1}, new_data={"a": 2}
        )
        assert event.entity_type == "TestEntity"
        assert event.old_data == {"a": 1}
        assert event.new_data == {"a": 2}

    def test_combined_event_has_both_attributes(self) -> None:
        from dataclasses import dataclass

        @dataclass(kw_only=True)
        class TestEvent(AuditableEvent, Event):
            id: UUID

        uid = uuid7.create()
        event = TestEvent(id=uid, entity_type="Test", new_data={"key": "value"})
        assert event.id == uid
        assert event.entity_type == "Test"
        assert event.execute_async is False
        assert isinstance(event, Event)
        assert isinstance(event, AuditableEvent)


class TestAuditLogEntity:
    """Testes para a entidade de leitura AuditLog."""

    def test_audit_log_creation_with_all_fields(self) -> None:
        uid = uuid7.create()
        entity_id = uuid7.create()
        now = datetime.now(timezone.utc)
        audit = AuditLogRead(
            id=uid,
            entity_type=EntityType.COMPANY,
            entity_id=entity_id,
            operation=AuditOperation.UPDATE,
            old_data={"a": 1},
            new_data={"a": 2},
            user_id=_TEST_USER_ID,
            created_at=now,
        )
        assert audit.entity_type == EntityType.COMPANY
        assert audit.operation == AuditOperation.UPDATE
        assert audit.user_id == _TEST_USER_ID

    def test_audit_log_optional_fields_default_none(self) -> None:
        audit = AuditLogRead(
            id=uuid7.create(),
            entity_type=EntityType.USER,
            entity_id=uuid7.create(),
            operation=AuditOperation.CREATE,
            created_at=datetime.now(timezone.utc),
        )
        assert audit.user_id is None
        assert audit.old_data is None
        assert audit.new_data is None

    def test_audit_log_is_frozen(self) -> None:
        audit = AuditLogRead(
            id=uuid7.create(),
            entity_type=EntityType.COMPANY,
            entity_id=uuid7.create(),
            operation=AuditOperation.CREATE,
            created_at=datetime.now(timezone.utc),
        )
        with pytest.raises(AttributeError):
            setattr(audit, "operation", "UPDATE")


class TestCompanyAuditData:
    """Testes para dados de auditoria emitidos pelo agregado Company."""

    def test_create_emits_audit_data_in_event(self) -> None:
        from business_contexts.domain.aggregate.company import Company
        from business_contexts.domain.events.company import CompanyCreated

        company = Company.create_aggregate(
            legal_name="Acme Corp",
            trade_name="Acme",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            cnpj="12345678000190",
            active=True,
        )
        company.create(password="secret123")
        events = [e for e in company.events if isinstance(e, CompanyCreated)]
        assert len(events) == 1
        event = events[0]
        assert event.entity_type == EntityType.COMPANY
        assert event.old_data is None
        assert event.new_data["legal_name"] == "Acme Corp"
        assert event.new_data["active"] is True

    def test_update_emits_old_and_new_data(self) -> None:
        from business_contexts.domain.aggregate.company import Company
        from business_contexts.domain.events.company import CompanyUpdated

        company = Company.create_aggregate(
            legal_name="Acme Corp",
            trade_name="Acme",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
        )
        company.update(legal_name="New Acme Corp", active=False)
        events = [e for e in company.events if isinstance(e, CompanyUpdated)]
        event = events[0]
        assert event.entity_type == EntityType.COMPANY
        assert event.old_data == {"legal_name": "Acme Corp", "active": True}
        assert event.new_data == {"legal_name": "New Acme Corp", "active": False}

    def test_update_only_changed_fields(self) -> None:
        from business_contexts.domain.aggregate.company import Company
        from business_contexts.domain.events.company import CompanyUpdated

        company = Company.create_aggregate(
            legal_name="Acme Corp",
            trade_name="Acme",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
        )
        company.update(email="new@acme.com")
        event = company.events[0]
        assert isinstance(event, CompanyUpdated)
        assert event.old_data == {"email": "contact@acme.com"}
        assert event.new_data == {"email": "new@acme.com"}

    def test_delete_emits_old_data(self) -> None:
        from business_contexts.domain.aggregate.company import Company
        from business_contexts.domain.events.company import CompanyDeleted

        company = Company.create_aggregate(
            legal_name="Acme Corp",
            trade_name="Acme",
            responsible_name="John Doe",
            email="contact@acme.com",
            cpf="12345678901",
            cnpj="12345678000190",
            active=True,
        )
        company.delete()
        events = [e for e in company.events if isinstance(e, CompanyDeleted)]
        event = events[0]
        assert event.entity_type == EntityType.COMPANY
        assert event.new_data is None
        assert event.old_data["legal_name"] == "Acme Corp"
        assert event.old_data["active"] is True


class TestUserAuditData:
    """Testes para dados de auditoria emitidos pelo agregado User."""

    def test_create_emits_audit_data(self) -> None:
        from business_contexts.domain.aggregate.user import User
        from business_contexts.domain.events.user import UserCreated

        user = User.create_aggregate(
            company=_TEST_COMPANY_ID,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
            active=True,
            admin=False,
        )
        user.create()
        events = [e for e in user.events if isinstance(e, UserCreated)]
        event = events[0]
        assert event.entity_type == EntityType.USER
        assert event.old_data is None
        assert event.new_data["email"] == "test@example.com"
        assert event.new_data["active"] is True

    def test_update_emits_old_and_new_data(self) -> None:
        from business_contexts.domain.aggregate.user import User
        from business_contexts.domain.events.user import UserUpdated

        user = User.create_aggregate(
            company=_TEST_COMPANY_ID,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.update(email="new@example.com", active=False)
        events = [e for e in user.events if isinstance(e, UserUpdated)]
        event = events[0]
        assert event.entity_type == EntityType.USER
        assert event.old_data["email"] == "test@example.com"
        assert event.new_data["email"] == "new@example.com"

    def test_update_password_is_redacted(self) -> None:
        from business_contexts.domain.aggregate.user import User
        from business_contexts.domain.events.user import UserUpdated

        user = User.create_aggregate(
            company=_TEST_COMPANY_ID,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.update(password="newpassword")
        event = user.events[0]
        assert isinstance(event, UserUpdated)
        assert event.new_data["password"] == AuditConstant.REDACTED_PASSWORD

    def test_delete_emits_old_data(self) -> None:
        from business_contexts.domain.aggregate.user import User
        from business_contexts.domain.events.user import UserDeleted

        user = User.create_aggregate(
            company=_TEST_COMPANY_ID,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
            admin=True,
        )
        user.delete()
        events = [e for e in user.events if isinstance(e, UserDeleted)]
        event = events[0]
        assert event.entity_type == EntityType.USER
        assert event.new_data is None
        assert event.old_data["email"] == "test@example.com"
        assert event.old_data["admin"] is True


class TestEventsAreAuditable:
    """Testes para garantir que os eventos de domínio são auditáveis."""

    def test_company_created_is_auditable(self) -> None:
        from business_contexts.domain.events.company import CompanyCreated

        event = CompanyCreated(id=uuid7.create())
        assert isinstance(event, AuditableEvent)
        assert isinstance(event, Event)

    def test_company_updated_is_auditable(self) -> None:
        from business_contexts.domain.events.company import CompanyUpdated

        assert isinstance(CompanyUpdated(id=uuid7.create()), AuditableEvent)

    def test_company_deleted_is_auditable(self) -> None:
        from business_contexts.domain.events.company import CompanyDeleted

        assert isinstance(CompanyDeleted(id=uuid7.create()), AuditableEvent)

    def test_user_created_is_auditable(self) -> None:
        from business_contexts.domain.events.user import UserCreated

        assert isinstance(
            UserCreated(id=uuid7.create(), company=_TEST_COMPANY_ID), AuditableEvent
        )

    def test_user_updated_is_auditable(self) -> None:
        from business_contexts.domain.events.user import UserUpdated

        assert isinstance(
            UserUpdated(id=uuid7.create(), company=_TEST_COMPANY_ID), AuditableEvent
        )

    def test_user_deleted_is_auditable(self) -> None:
        from business_contexts.domain.events.user import UserDeleted

        assert isinstance(
            UserDeleted(id=uuid7.create(), company=_TEST_COMPANY_ID), AuditableEvent
        )


class TestAuditLogDomainRegistration:
    """Testes para o registro do domínio audit_log no enum Domain."""

    def test_audit_log_domain_exists(self) -> None:
        from messagebus.domains import Domain

        assert hasattr(Domain, "audit_log")

    def test_audit_log_domain_has_domain_repo(self) -> None:
        from business_contexts.adapters.repository.domain_repo.audit_log import (
            AuditLogDomainRepo,
        )
        from messagebus.domains import Domain

        assert Domain.audit_log.value[0] is AuditLogDomainRepo

    def test_audit_log_domain_has_view_repo(self) -> None:
        from business_contexts.adapters.repository.view_repo.audit_log import (
            AuditLogViewRepo,
        )
        from messagebus.domains import Domain

        assert Domain.audit_log.value[1] is AuditLogViewRepo


class TestAuditHandlersRegistration:
    """Testes para o registro dos handlers de auditoria nos event handlers."""

    def test_company_events_have_audit_handlers(self) -> None:
        from business_contexts.domain.events.company import (
            CompanyCreated,
            CompanyDeleted,
            CompanyUpdated,
        )
        from messagebus.handlers import EVENT_HANDLERS
        from business_contexts.services.handlers.audit_log import (
            audit_entity_created,
            audit_entity_deleted,
            audit_entity_updated,
        )

        assert audit_entity_created in EVENT_HANDLERS[CompanyCreated]
        assert audit_entity_updated in EVENT_HANDLERS[CompanyUpdated]
        assert audit_entity_deleted in EVENT_HANDLERS[CompanyDeleted]

    def test_user_events_have_audit_handlers(self) -> None:
        from business_contexts.domain.events.user import (
            UserCreated,
            UserDeleted,
            UserUpdated,
        )
        from messagebus.handlers import EVENT_HANDLERS
        from business_contexts.services.handlers.audit_log import (
            audit_entity_created,
            audit_entity_deleted,
            audit_entity_updated,
        )

        assert audit_entity_created in EVENT_HANDLERS[UserCreated]
        assert audit_entity_updated in EVENT_HANDLERS[UserUpdated]
        assert audit_entity_deleted in EVENT_HANDLERS[UserDeleted]


class TestAuditBase:
    """Testes para a classe base AuditBase."""

    def test_audit_base_default_values(self) -> None:
        from messagebus.entities import AuditBase

        audit = AuditBase()
        assert audit.active is True
        assert audit.created_at is None
        assert audit.created_by is None
        assert audit.deleted_at is None
        assert audit.deleted_by is None

    def test_audit_base_is_deleted_false_when_no_deleted_at(self) -> None:
        from messagebus.entities import AuditBase

        assert AuditBase().is_deleted is False

    def test_audit_base_is_deleted_true_when_set(self) -> None:
        from messagebus.entities import AuditBase

        assert AuditBase(deleted_at=datetime.now(timezone.utc)).is_deleted is True

    def test_audit_read_base_is_frozen(self) -> None:
        from messagebus.entities import AuditReadBase

        audit = AuditReadBase()
        with pytest.raises((AttributeError, TypeError)):
            setattr(audit, "active", False)

    def test_aggregate_inherits_audit_base(self) -> None:
        from messagebus.entities import Aggregate, AuditBase

        assert issubclass(Aggregate, AuditBase)

    def test_aggregate_set_create_audit(self) -> None:
        from business_contexts.domain.aggregate.company import Company

        company = Company.create_aggregate(
            legal_name="Test",
            trade_name=None,
            responsible_name="John",
            email="t@t.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
        )
        uid = uuid7.create()
        company._set_create_audit(uid)
        assert company.created_at is not None
        assert company.created_by == uid

    def test_aggregate_set_delete_audit(self) -> None:
        from business_contexts.domain.aggregate.company import Company

        company = Company.create_aggregate(
            legal_name="Test",
            trade_name=None,
            responsible_name="John",
            email="t@t.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
        )
        uid = uuid7.create()
        company._set_delete_audit(uid)
        assert company.deleted_at is not None
        assert company.deleted_by == uid
        assert company.is_deleted is True
