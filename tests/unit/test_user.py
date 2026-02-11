"""Testes unitários para o fluxo de User."""

from uuid import UUID

import uuid7

from messagebus.entities import Aggregate, OperationType, UserSecurity
from business_contexts.domain.aggregate.user import User
from business_contexts.domain.commands.user import (
    CreateUser,
    UpdateUser,
    DeleteUser,
)
from business_contexts.domain.entitites.user import User as UserEntity
from business_contexts.domain.events.user import (
    UserCreated,
    UserUpdated,
    UserDeleted,
    TimeToCreateInitialCompanyUser,
    TimeToCreateCompanyAdminUser,
)
from business_contexts.entrypoints.schemas.user import (
    CreateUserSchema,
    UpdateUserSchema,
    ReadUserSchema,
)


class TestUserAggregate:
    """Testes para o agregado User."""

    def test_create_aggregate_returns_user_with_uuid(self) -> None:
        """Verifica que create_aggregate retorna um User com UUID válido."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

        assert isinstance(user.id, UUID)
        assert user.company == company_id
        assert user.email == "test@example.com"
        assert user.cpf == "12345678901"
        assert user.password == "secret123"
        assert user.active is True
        assert user.admin is False
        assert user.deleted is False

    def test_create_aggregate_generates_unique_ids(self) -> None:
        """Verifica que cada chamada gera um ID diferente."""
        company_id = uuid7.create()
        user1 = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
        )
        user2 = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
        )

        assert user1.id != user2.id

    def test_user_inherits_from_aggregate(self) -> None:
        """Verifica que User herda de Aggregate."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )

        assert isinstance(user, Aggregate)

    def test_create_sets_insert_operation_type(self) -> None:
        """Verifica que create() define o tipo de operação como INSERT."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.create()

        assert user._operation_type == OperationType.INSERT

    def test_create_emits_user_created_event(self) -> None:
        """Verifica que create() emite o evento UserCreated."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
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
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.update(email="new@example.com")

        assert user._operation_type == OperationType.UPDATE

    def test_update_changes_email(self) -> None:
        """Verifica que update() altera o email do usuário."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.update(email="new@example.com")

        assert user.email == "new@example.com"

    def test_update_changes_password(self) -> None:
        """Verifica que update() altera a senha do usuário."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.update(password="newpassword")

        assert user.password == "newpassword"

    def test_update_changes_active(self) -> None:
        """Verifica que update() altera o status de ativação."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123", active=True
        )
        user.update(active=False)

        assert user.active is False

    def test_update_changes_admin(self) -> None:
        """Verifica que update() altera o status de administrador."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123", admin=False
        )
        user.update(admin=True)

        assert user.admin is True

    def test_update_with_none_does_not_change_fields(self) -> None:
        """Verifica que update() com None não altera os campos."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.update(email=None, password=None, active=None, admin=None)

        assert user.email == "test@example.com"
        assert user.password == "secret123"
        assert user.active is True
        assert user.admin is False

    def test_update_emits_user_updated_event(self) -> None:
        """Verifica que update() emite o evento UserUpdated."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.update(email="new@example.com")

        assert len(user.events) == 1
        event = user.events[0]
        assert isinstance(event, UserUpdated)
        assert event.id == user.id
        assert event.company == company_id

    def test_delete_sets_delete_operation_type(self) -> None:
        """Verifica que delete() define o tipo de operação como DELETE (soft delete)."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.delete()

        assert user._operation_type == OperationType.DELETE
        assert user.deleted is True

    def test_delete_emits_user_deleted_event(self) -> None:
        """Verifica que delete() emite o evento UserDeleted."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
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
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.create()
        user.update(email="new@example.com")

        assert len(user.events) == 2
        assert isinstance(user.events[0], UserCreated)
        assert isinstance(user.events[1], UserUpdated)

    def test_hash_is_based_on_id(self) -> None:
        """Verifica que o hash é baseado no ID."""
        user = User.create_aggregate(
            company=uuid7.create(), email="test@example.com", cpf="12345678901", password="secret123"
        )

        assert hash(user) == hash(user.id)

    def test_create_aggregate_with_custom_active_admin(self) -> None:
        """Verifica que create_aggregate aceita valores customizados de active e admin."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="admin@example.com",
            cpf="12345678901",
            password="secret123",
            active=False,
            admin=True,
        )

        assert user.active is False
        assert user.admin is True


class TestUserCommands:
    """Testes para os comandos de User."""

    def test_create_user_command(self) -> None:
        """Verifica a criação do comando CreateUser."""
        company_id = uuid7.create()
        command = CreateUser(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

        assert command.company == company_id
        assert command.email == "test@example.com"
        assert command.cpf == "12345678901"
        assert command.password == "secret123"
        assert command.active is True
        assert command.admin is False

    def test_create_user_command_custom_flags(self) -> None:
        """Verifica a criação do CreateUser com active/admin customizados."""
        command = CreateUser(
            company=uuid7.create(),
            email="admin@example.com",
            cpf="12345678901",
            password="secret123",
            active=False,
            admin=True,
        )

        assert command.active is False
        assert command.admin is True

    def test_update_user_command(self) -> None:
        """Verifica a criação do comando UpdateUser."""
        command = UpdateUser(
            email="test@example.com",
            new_email="new@example.com",
            new_password="newpassword",
            new_active=False,
            new_admin=True,
        )

        assert command.email == "test@example.com"
        assert command.new_email == "new@example.com"
        assert command.new_password == "newpassword"
        assert command.new_active is False
        assert command.new_admin is True

    def test_update_user_command_optional_fields(self) -> None:
        """Verifica que campos opcionais do UpdateUser são None por padrão."""
        command = UpdateUser(email="test@example.com")

        assert command.new_email is None
        assert command.new_password is None
        assert command.new_active is None
        assert command.new_admin is None

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

    def test_time_to_create_initial_company_user_event(self) -> None:
        """Verifica a criação do evento TimeToCreateInitialCompanyUser."""
        company_id = uuid7.create()
        event = TimeToCreateInitialCompanyUser(
            company=company_id,
            name="John Doe",
            email="john@example.com",
            cpf="12345678901",
            password="secret123",
            active=True,
            admin=True,
        )

        assert event.company == company_id
        assert event.name == "John Doe"
        assert event.email == "john@example.com"
        assert event.cpf == "12345678901"
        assert event.password == "secret123"
        assert event.active is True
        assert event.admin is True

    def test_time_to_create_company_admin_user_event(self) -> None:
        """Verifica a criação do evento TimeToCreateCompanyAdminUser com defaults."""
        company_id = uuid7.create()
        event = TimeToCreateCompanyAdminUser(
            company=company_id,
            email="admin@example.com",
        )

        assert event.company == company_id
        assert event.email == "admin@example.com"
        assert event.name == "Admin User"
        assert event.active is True
        assert event.admin is True


class TestUserEntity:
    """Testes para a entidade de leitura User."""

    def test_user_entity_creation(self) -> None:
        """Verifica a criação da entidade User com todos os campos."""
        uid = uuid7.create()
        company_id = uuid7.create()
        entity = UserEntity(
            id=uid,
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            active=True,
            admin=False,
            deleted=False,
        )

        assert entity.id == uid
        assert entity.company == company_id
        assert entity.email == "test@example.com"
        assert entity.cpf == "12345678901"
        assert entity.active is True
        assert entity.admin is False
        assert entity.deleted is False

    def test_user_entity_inherits_user_security(self) -> None:
        """Verifica que a entidade User herda de UserSecurity."""
        entity = UserEntity(
            id=uuid7.create(),
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            active=True,
            admin=False,
            deleted=False,
        )

        assert isinstance(entity, UserSecurity)


class TestUserSchemas:
    """Testes para os schemas de User."""

    def test_create_user_schema(self) -> None:
        """Verifica o schema de criação de usuário."""
        company_id = uuid7.create()
        schema = CreateUserSchema(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
            active=True,
            admin=False,
        )

        assert schema.company == company_id
        assert schema.email == "test@example.com"
        assert schema.cpf == "12345678901"
        assert schema.password == "secret123"
        assert schema.active is True
        assert schema.admin is False

    def test_update_user_schema(self) -> None:
        """Verifica o schema de atualização de usuário."""
        company_id = uuid7.create()
        schema = UpdateUserSchema(
            company=company_id,
            email="test@example.com",
            new_email="new@example.com",
            new_password="newpwd",
            new_active=False,
            new_admin=True,
        )

        assert schema.company == company_id
        assert schema.email == "test@example.com"
        assert schema.new_email == "new@example.com"
        assert schema.new_password == "newpwd"
        assert schema.new_active is False
        assert schema.new_admin is True

    def test_update_user_schema_optional_fields(self) -> None:
        """Verifica que campos opcionais do UpdateUserSchema são None por padrão."""
        company_id = uuid7.create()
        schema = UpdateUserSchema(company=company_id, email="test@example.com")

        assert schema.new_email is None
        assert schema.new_password is None
        assert schema.new_active is None
        assert schema.new_admin is None

    def test_read_user_schema(self) -> None:
        """Verifica o schema de leitura de usuário."""
        uid = uuid7.create()
        company_id = uuid7.create()
        schema = ReadUserSchema(
            id=uid,
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            active=True,
            admin=False,
            deleted=False,
        )

        assert schema.id == uid
        assert schema.company == company_id
        assert schema.email == "test@example.com"
        assert schema.cpf == "12345678901"
        assert schema.active is True
        assert schema.admin is False
        assert schema.deleted is False


class TestUserAggregateBelongsToCompany:
    """Testes para garantir que usuários pertencem a uma empresa."""

    def test_user_aggregate_has_company_field(self) -> None:
        """Verifica que o agregado User possui campo company obrigatório."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
        )

        assert user.company == company_id

    def test_user_created_event_carries_company(self) -> None:
        """Verifica que o evento UserCreated carrega o ID da empresa."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id, email="test@example.com", cpf="12345678901", password="secret123"
        )
        user.create()

        event = user.events[0]
        assert isinstance(event, UserCreated)
        assert event.company == company_id

    def test_different_companies_produce_different_events(self) -> None:
        """Verifica que usuários de empresas diferentes emitem eventos com company diferente."""
        company_a = uuid7.create()
        company_b = uuid7.create()

        user_a = User.create_aggregate(
            company=company_a, email="a@example.com", cpf="12345678901", password="pwd"
        )
        user_b = User.create_aggregate(
            company=company_b, email="b@example.com", cpf="12345678902", password="pwd"
        )
        user_a.create()
        user_b.create()

        assert user_a.events[0].company == company_a
        assert user_b.events[0].company == company_b
        assert user_a.events[0].company != user_b.events[0].company
