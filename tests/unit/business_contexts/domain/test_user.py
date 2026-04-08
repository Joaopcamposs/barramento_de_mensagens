"""Testes unitários para o fluxo de User."""

from uuid import UUID

import uuid7

from business_contexts.security import UserSecurity
from messagebus.entities import Aggregate, OperationType

_TEST_COMPANY_ID = uuid7.create()
from business_contexts.domain.aggregate.user import PublicUser, User
from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.commands.user import (
    CreateUser,
    DeleteUser,
    UpdateUser,
)
from business_contexts.domain.entitites.user import PublicUser as PublicUserEntity
from business_contexts.domain.entitites.user import User as UserEntity
from business_contexts.domain.events.user import (
    TimeToCreateCompanyAdminUser,
    TimeToCreateInitialCompanyUser,
    UserCreated,
    UserDeleted,
    UserUpdated,
)
from business_contexts.domain.excecoes import (
    CompanyAlreadyRegistered,
    CompanyNotFound,
    CredentialsException,
    UserAlreadyRegistered,
    UserNotFound,
)
from business_contexts.entrypoints.schemas.security import Token, TokenData
from business_contexts.entrypoints.schemas.user import (
    CreateUserSchema,
    ReadUserSchema,
    UpdateUserSchema,
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
        assert user.password_hash != "secret123"  # senha é hasheada pelo bcrypt
        assert user.password_hash.startswith("$2b$")
        assert user.active is True
        assert user.admin is False
        assert user.deleted_at is None

    def test_create_aggregate_generates_unique_ids(self) -> None:
        """Verifica que cada chamada gera um ID diferente."""
        company_id = uuid7.create()
        user1 = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user2 = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

        assert user1.id != user2.id

    def test_user_inherits_from_aggregate(self) -> None:
        """Verifica que User herda de Aggregate."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

        assert isinstance(user, Aggregate)

    def test_create_sets_insert_operation_type(self) -> None:
        """Verifica que create() define o tipo de operação como INSERT."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.create()

        assert user._operation_type == OperationType.INSERT

    def test_create_emits_user_created_event(self) -> None:
        """Verifica que create() emite o evento UserCreated."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.create()

        assert len(user.events) == 1
        event = user.events[0]
        assert isinstance(event, UserCreated)
        assert event.id == user.id
        assert event.company == company_id

    def test_user_update_sets_update_operation_type(self) -> None:
        """Verifica que update() define o tipo de operação como UPDATE."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.update(email="new@example.com")

        assert user._operation_type == OperationType.UPDATE

    def test_update_changes_email(self) -> None:
        """Verifica que update() altera o email do usuário."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.update(email="new@example.com")

        assert user.email == "new@example.com"

    def test_update_changes_password(self) -> None:
        """Verifica que update() altera a senha do usuário."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.update(password="newpassword")

        assert user.password_hash.startswith("$2b$")

    def test_update_changes_active(self) -> None:
        """Verifica que update() altera o status de ativação."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
            active=True,
        )
        user.update(active=False)

        assert user.active is False

    def test_update_changes_admin(self) -> None:
        """Verifica que update() altera o status de administrador."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
            admin=False,
        )
        user.update(admin=True)

        assert user.admin is True

    def test_update_with_none_does_not_change_fields(self) -> None:
        """Verifica que update() com None não altera os campos."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        original_password = user.password_hash
        user.update(email=None, password=None, active=None, admin=None)

        assert user.email == "test@example.com"
        assert user.password_hash == original_password
        assert user.active is True
        assert user.admin is False

    def test_update_emits_user_updated_event(self) -> None:
        """Verifica que update() emite o evento UserUpdated."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
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
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.delete()

        assert user._operation_type == OperationType.DELETE
        assert user.is_deleted is True

    def test_delete_emits_user_deleted_event(self) -> None:
        """Verifica que delete() emite o evento UserDeleted."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
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
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )
        user.create()
        user.update(email="new@example.com")

        assert len(user.events) == 2
        assert isinstance(user.events[0], UserCreated)
        assert isinstance(user.events[1], UserUpdated)

    def test_user_hash_is_based_on_id(self) -> None:
        """Verifica que o hash é baseado no ID."""
        user = User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
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
        command = CreateUser(
            company=_TEST_COMPANY_ID,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

        assert command.company == _TEST_COMPANY_ID
        assert command.email == "test@example.com"
        assert command.cpf == "12345678901"
        assert command.password == "secret123"
        assert command.active is True
        assert command.admin is False

    def test_create_user_command_custom_flags(self) -> None:
        """Verifica a criação do CreateUser com active/admin customizados."""
        command = CreateUser(
            company=_TEST_COMPANY_ID,
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
        )

        assert entity.id == uid
        assert entity.company == company_id
        assert entity.email == "test@example.com"
        assert entity.cpf == "12345678901"
        assert entity.active is True
        assert entity.admin is False
        assert entity.deleted_at is None

    def test_user_entity_inherits_user_security(self) -> None:
        """Verifica que a entidade User herda de UserSecurity."""
        entity = UserEntity(
            id=uuid7.create(),
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            active=True,
            admin=False,
        )

        assert isinstance(entity, UserSecurity)


class TestUserSchemas:
    """Testes para os schemas de User."""

    def test_create_user_schema(self) -> None:
        """Verifica o schema de criação de usuário."""
        schema = CreateUserSchema(
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
            active=True,
            admin=False,
        )

        assert schema.email == "test@example.com"
        assert schema.cpf == "12345678901"
        assert schema.password == "secret123"
        assert schema.active is True
        assert schema.admin is False

    def test_update_user_schema(self) -> None:
        """Verifica o schema de atualização de usuário."""
        schema = UpdateUserSchema(
            new_email="new@example.com",
            new_password="newpwd",
            new_active=False,
            new_admin=True,
        )

        assert schema.new_email == "new@example.com"
        assert schema.new_email == "new@example.com"
        assert schema.new_password == "newpwd"
        assert schema.new_active is False
        assert schema.new_admin is True

    def test_update_user_schema_optional_fields(self) -> None:
        """Verifica que campos opcionais do UpdateUserSchema são None por padrão."""
        schema = UpdateUserSchema()

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
        )

        assert schema.id == uid
        assert schema.company == company_id
        assert schema.email == "test@example.com"
        assert schema.cpf == "12345678901"
        assert schema.active is True
        assert schema.admin is False


class TestUserAggregateBelongsToCompany:
    """Testes para garantir que usuários pertencem a uma empresa."""

    def test_user_aggregate_has_company_field(self) -> None:
        """Verifica que o agregado User possui campo company obrigatório."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

        assert user.company == company_id

    def test_user_created_event_carries_company(self) -> None:
        """Verifica que o evento UserCreated carrega o ID da empresa."""
        company_id = uuid7.create()
        user = User.create_aggregate(
            company=company_id,
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
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


class TestPublicUserAggregate:
    """Testes para o agregado PublicUser."""

    @staticmethod
    def _make_user() -> User:
        """Função auxiliar para criar um agregado User."""
        return User.create_aggregate(
            company=uuid7.create(),
            email="test@example.com",
            cpf="12345678901",
            password="secret123",
        )

    def test_create_registration_aggregate_returns_public_user(self) -> None:
        """Verifica que create_registration_aggregate retorna um PublicUser válido."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)

        assert isinstance(public_user, PublicUser)
        assert public_user.id == user.id
        assert public_user.company == user.company
        assert public_user.active == user.active
        assert isinstance(public_user.email_encrypted, bytes)
        assert isinstance(public_user.email_hash, str)
        assert len(public_user.email_hash) == 64  # SHA-256 hex digest

    def test_create_registration_aggregate_encrypts_email(self) -> None:
        """Verifica que o email é criptografado e diferente do original."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)

        assert public_user.email_encrypted != user.email.encode()
        assert len(public_user.email_encrypted) > 0

    def test_create_registration_aggregate_hashes_email(self) -> None:
        """Verifica que o hash do email é consistente."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)

        expected_hash = UserSecurity.hash_email(user.email)
        assert public_user.email_hash == expected_hash

    def test_public_user_inherits_from_aggregate(self) -> None:
        """Verifica que PublicUser herda de Aggregate."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)

        assert isinstance(public_user, Aggregate)

    def test_public_user_inherits_from_user_security(self) -> None:
        """Verifica que PublicUser herda de UserSecurity."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)

        assert isinstance(public_user, UserSecurity)

    def test_register_sets_insert_operation_type(self) -> None:
        """Verifica que register() define o tipo de operação como INSERT."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)
        public_user.register()

        assert public_user._operation_type == OperationType.INSERT

    def test_public_user_update_sets_update_operation_type(self) -> None:
        """Verifica que update() define o tipo de operação como UPDATE."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)
        public_user.update(email="new@example.com", password="newhash", active=False)

        assert public_user._operation_type == OperationType.UPDATE

    def test_update_changes_email_encrypted_and_hash(self) -> None:
        """Verifica que update() altera o email criptografado e o hash."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)
        original_encrypted = public_user.email_encrypted
        original_hash = public_user.email_hash

        public_user.update(email="new@example.com", password="newhash", active=True)

        assert public_user.email_encrypted != original_encrypted
        assert public_user.email_hash != original_hash
        assert public_user.email_hash == UserSecurity.hash_email("new@example.com")

    def test_update_changes_password_and_active(self) -> None:
        """Verifica que update() altera senha e status de ativação."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)
        public_user.update(email="test@example.com", password="newpasshash", active=False)

        assert public_user._password_hash == "newpasshash"
        assert public_user.active is False

    def test_remove_sets_delete_operation_type(self) -> None:
        """Verifica que remove() define o tipo de operação como DELETE."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)
        public_user.remove()

        assert public_user._operation_type == OperationType.DELETE

    def test_public_user_hash_is_based_on_id(self) -> None:
        """Verifica que o hash do PublicUser é baseado no ID."""
        user = self._make_user()
        public_user = PublicUser.create_registration_aggregate(user=user)

        assert hash(public_user) == hash(public_user.id)


class TestPublicUserEntity:
    """Testes para a entidade de leitura PublicUser."""

    def test_public_user_entity_creation(self) -> None:
        """Verifica a criação da entidade PublicUser com todos os campos."""
        uid = uuid7.create()
        company_id = uuid7.create()
        entity = PublicUserEntity(
            id=uid,
            company=company_id,
            active=True,
            email_encrypted=b"encrypted_data",
            email_hash="a" * 64,
        )

        assert entity.id == uid
        assert entity.company == company_id
        assert entity.active is True
        assert entity.email_encrypted == b"encrypted_data"
        assert entity.email_hash == "a" * 64

    def test_public_user_entity_inherits_user_security(self) -> None:
        """Verifica que a entidade PublicUser herda de UserSecurity."""
        entity = PublicUserEntity(
            id=uuid7.create(),
            company=uuid7.create(),
            active=True,
            email_encrypted=b"encrypted_data",
            email_hash="a" * 64,
        )

        assert isinstance(entity, UserSecurity)


class TestUserSecurity:
    """Testes para o mixin UserSecurity."""

    def test_encrypt_password_returns_bcrypt_hash(self) -> None:
        """Verifica que encrypt_password retorna um hash bcrypt."""
        hashed = UserSecurity.encrypt_password("mypassword")

        assert hashed.startswith("$2b$")
        assert hashed != "mypassword"

    def test_encrypt_password_generates_different_hashes(self) -> None:
        """Verifica que encrypt_password gera hashes diferentes para a mesma senha."""
        hash1 = UserSecurity.encrypt_password("mypassword")
        hash2 = UserSecurity.encrypt_password("mypassword")

        assert hash1 != hash2  # salt diferente

    def test_verify_password_with_correct_password(self) -> None:
        """Verifica que verify_password retorna True para senha correta."""
        password = "secret123"
        hashed = UserSecurity.encrypt_password(password)
        security = UserSecurity(_password_hash=hashed)

        assert security.verify_password(password) is True

    def test_verify_password_with_wrong_password(self) -> None:
        """Verifica que verify_password retorna False para senha incorreta."""
        hashed = UserSecurity.encrypt_password("secret123")
        security = UserSecurity(_password_hash=hashed)

        assert security.verify_password("wrong_password") is False

    def test_hash_email_returns_sha256_hex(self) -> None:
        """Verifica que hash_email retorna um hash SHA-256 hexadecimal."""
        email_hash = UserSecurity.hash_email("test@example.com")

        assert len(email_hash) == 64
        assert all(c in "0123456789abcdef" for c in email_hash)

    def test_hash_email_is_deterministic(self) -> None:
        """Verifica que hash_email retorna o mesmo hash para o mesmo email."""
        hash1 = UserSecurity.hash_email("test@example.com")
        hash2 = UserSecurity.hash_email("test@example.com")

        assert hash1 == hash2

    def test_hash_email_normalizes_case_and_whitespace(self) -> None:
        """Verifica que hash_email normaliza maiúsculas e espaços."""
        hash1 = UserSecurity.hash_email("Test@Example.com")
        hash2 = UserSecurity.hash_email("  test@example.com  ")

        assert hash1 == hash2

    def test_hash_email_different_emails_different_hashes(self) -> None:
        """Verifica que emails diferentes geram hashes diferentes."""
        hash1 = UserSecurity.hash_email("a@example.com")
        hash2 = UserSecurity.hash_email("b@example.com")

        assert hash1 != hash2

    def test_encrypt_and_decrypt_email(self) -> None:
        """Verifica que encrypt_email e decrypt_email são reversíveis."""
        email = "test@example.com"
        encrypted = UserSecurity.encrypt_email(email)
        decrypted = UserSecurity.decrypt_email(encrypted)

        assert decrypted == email
        assert encrypted != email.encode()

    def test_encrypt_email_generates_different_ciphertexts(self) -> None:
        """Verifica que encrypt_email gera cifras diferentes (nonce aleatório)."""
        email = "test@example.com"
        enc1 = UserSecurity.encrypt_email(email)
        enc2 = UserSecurity.encrypt_email(email)

        assert enc1 != enc2  # nonce diferente a cada chamada


class TestAuthenticateUserCommand:
    """Testes para o comando AuthenticateUser."""

    def test_authenticate_user_command(self) -> None:
        """Verifica a criação do comando AuthenticateUser."""
        command = AuthenticateUser(
            email="test@example.com",
            password="secret123",
        )

        assert command.email == "test@example.com"
        assert command.password == "secret123"


class TestSecuritySchemas:
    """Testes para os schemas de segurança."""

    def test_token_schema(self) -> None:
        """Verifica o schema Token."""
        token = Token(access_token="abc123", token_type="bearer")

        assert token.access_token == "abc123"
        assert token.token_type == "bearer"

    def test_token_data_schema(self) -> None:
        """Verifica o schema TokenData."""
        data = TokenData(username="test@example.com")

        assert data.username == "test@example.com"

    def test_token_data_schema_default_none(self) -> None:
        """Verifica que username é None por padrão."""
        data = TokenData()

        assert data.username is None


class TestDomainExceptions:
    """Testes para as exceções de domínio."""

    def test_user_already_registered_exception(self) -> None:
        """Verifica a exceção UserAlreadyRegistered."""
        exc = UserAlreadyRegistered()

        assert exc.status_code == 409
        assert exc.detail == "User email already registered"

    def test_user_not_found_exception(self) -> None:
        """Verifica a exceção UserNotFound."""
        exc = UserNotFound()

        assert exc.status_code == 404
        assert exc.detail == "User not found"

    def test_company_already_registered_exception(self) -> None:
        """Verifica a exceção CompanyAlreadyRegistered."""
        exc = CompanyAlreadyRegistered()

        assert exc.status_code == 409
        assert exc.detail == "Company name already registered"

    def test_company_not_found_exception(self) -> None:
        """Verifica a exceção CompanyNotFound."""
        exc = CompanyNotFound()

        assert exc.status_code == 404
        assert exc.detail == "Company not found"

    def test_credentials_exception(self) -> None:
        """Verifica a exceção CredentialsException."""
        exc = CredentialsException()

        assert exc.status_code == 401
        assert exc.detail == "Could not validate credentials"
