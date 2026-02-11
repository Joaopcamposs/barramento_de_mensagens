"""Testes unitários para o fluxo de User."""

from uuid import UUID

import uuid7

from messagebus.entities import Aggregate, OperationType
from business_contexts.domain.aggregate.user import User
from business_contexts.domain.commands.user import (
    CreateUser,
    UpdateUser,
    DeleteUser,
)
from business_contexts.domain.events.user import (
    UserCreated,
    UserUpdated,
    UserDeleted,
)


class TestUserAggregate:
    """Testes para o agregado User."""

    def test_create_aggregate_returns_user_with_uuid(self) -> None:
        """Verifica que create_aggregate retorna um User com UUID válido."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", password="secret123"
        )

        assert isinstance(user.id, UUID)
        assert user.company == company_id
        assert user.email == "test@example.com"
        assert user.password == "secret123"
        assert user.deleted is False

    def test_create_aggregate_generates_unique_ids(self) -> None:
        """Verifica que cada chamada gera um ID diferente."""
        company_id = uuid7.create()
        user1 = User.create_aggregate(
            company=company_id, email="test@example.com", password="secret123"
        )
        user2 = User.create_aggregate(
            company=company_id, email="test@example.com", password="secret123"
        )

        assert user1.id != user2.id

    def test_user_inherits_from_aggregate(self) -> None:
        """Verifica que User herda de Aggregate."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )

        assert isinstance(user, Aggregate)

    def test_create_sets_insert_operation_type(self) -> None:
        """Verifica que create() define o tipo de operação como INSERT."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.create()

        assert user._operation_type == OperationType.INSERT

    def test_create_emits_user_created_event(self) -> None:
        """Verifica que create() emite o evento UserCreated."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", password="secret123"
        )
        user.create()

        assert len(user.events) == 1
        event = user.events[0]
        assert isinstance(event, UserCreated)
        assert event.id == user.id
        assert event.company == company_id

    def test_update_sets_update_operation_type(self) -> None:
        """Verifica que update() define o tipo de operação como UPDATE."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.update(email="new@example.com")

        assert user._operation_type == OperationType.UPDATE

    def test_update_changes_email(self) -> None:
        """Verifica que update() altera o email do usuário."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.update(email="new@example.com")

        assert user.email == "new@example.com"

    def test_update_changes_password(self) -> None:
        """Verifica que update() altera a senha do usuário."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.update(password="newpassword")

        assert user.password == "newpassword"

    def test_update_with_none_does_not_change_fields(self) -> None:
        """Verifica que update() com None não altera os campos."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.update(email=None, password=None)

        assert user.email == "test@example.com"
        assert user.password == "secret123"

    def test_update_emits_user_updated_event(self) -> None:
        """Verifica que update() emite o evento UserUpdated."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", password="secret123"
        )
        user.update(email="new@example.com")

        assert len(user.events) == 1
        event = user.events[0]
        assert isinstance(event, UserUpdated)
        assert event.id == user.id
        assert event.company == company_id

    def test_delete_sets_update_operation_type(self) -> None:
        """Verifica que delete() define o tipo de operação como UPDATE (soft delete)."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.delete()

        assert user._operation_type == OperationType.DELETE
        assert user.deleted is True

    def test_delete_emits_user_deleted_event(self) -> None:
        """Verifica que delete() emite o evento UserDeleted."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", password="secret123"
        )
        user.delete()

        assert len(user.events) == 1
        event = user.events[0]
        assert isinstance(event, UserDeleted)
        assert event.id == user.id
        assert event.company == company_id

    def test_multiple_operations_accumulate_events(self) -> None:
        """Verifica que múltiplas operações acumulam eventos."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )
        user.create()
        user.update(email="new@example.com")

        assert len(user.events) == 2
        assert isinstance(user.events[0], UserCreated)
        assert isinstance(user.events[1], UserUpdated)

    def test_hash_is_based_on_id(self) -> None:
        """Verifica que o hash é baseado no ID."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", password="secret123"
        )

        assert hash(user) == hash(user.id)


class TestUserCommands:
    """Testes para os comandos de User."""

    def test_create_user_command(self) -> None:
        """Verifica a criação do comando CreateUser."""
        company_id = uuid7.create()
        command = CreateUser(
            company=company_id, email="test@example.com", password="secret123"
        )

        assert command.company == company_id
        assert command.email == "test@example.com"
        assert command.password == "secret123"

    def test_update_user_command(self) -> None:
        """Verifica a criação do comando UpdateUser."""
        command = UpdateUser(
            email="test@example.com",
            new_email="new@example.com",
            new_password="newpassword",
        )

        assert command.email == "test@example.com"
        assert command.new_email == "new@example.com"
        assert command.new_password == "newpassword"

    def test_update_user_command_optional_fields(self) -> None:
        """Verifica que campos opcionais do UpdateUser são None por padrão."""
        command = UpdateUser(email="test@example.com")

        assert command.new_email is None
        assert command.new_password is None

    def test_delete_user_command(self) -> None:
        """Verifica a criação do comando DeleteUser."""
        command = DeleteUser(email="test@example.com")

        assert command.email == "test@example.com"


class TestUserEvents:
    """Testes para os eventos de User."""

    def test_user_created_event(self) -> None:
        """Verifica a criação do evento UserCreated."""
        uid = uuid7.create()
        company_id = uuid7.create()
        event = UserCreated(id=uid, company=company_id)

        assert event.id == uid
        assert event.company == company_id

    def test_user_updated_event(self) -> None:
        """Verifica a criação do evento UserUpdated."""
        uid = uuid7.create()
        company_id = uuid7.create()
        event = UserUpdated(id=uid, company=company_id)

        assert event.id == uid
        assert event.company == company_id

    def test_user_deleted_event(self) -> None:
        """Verifica a criação do evento UserDeleted."""
        uid = uuid7.create()
        company_id = uuid7.create()
        event = UserDeleted(id=uid, company=company_id)

        assert event.id == uid
        assert event.company == company_id
