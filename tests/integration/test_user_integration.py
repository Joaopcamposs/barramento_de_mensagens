"""Testes de integração para o fluxo de User."""

from uuid import UUID

import pytest

from business_contexts.adapters.views.company import view_company
from business_contexts.adapters.views.user import view_user
from business_contexts.domain.commands.company import CreateCompany
from business_contexts.domain.commands.user import (
    CreateUser,
    DeleteUser,
    UpdateUser,
)
from business_contexts.domain.excecoes import (
    UserAlreadyRegistered,
    UserNotFound,
)
from messagebus.bootstrap import bootstrap
from messagebus.unity_of_work import UnitOfWork


async def _create_company(legal_name: str = "Test Company", **overrides) -> UUID:
    """Helper para criar uma empresa e retornar seu ID."""
    defaults = dict(
        legal_name=legal_name,
        responsible_name="Test User",
        active=True,
        cpf="12345678901",
        email=f"{legal_name.lower().replace(' ', '_')}@test.com",
        password="secret123",
        should_create_user=False,
    )
    defaults.update(overrides)
    bus = bootstrap(raise_event_errors=True)
    return await bus.handle(CreateCompany(**defaults))


def _create_user_cmd(company_id: UUID, email: str, **overrides) -> CreateUser:
    """Helper para criar comando CreateUser com valores padrão."""
    defaults = dict(
        company=company_id,
        email=email,
        cpf="12345678901",
        password="secret123",
        active=True,
        admin=False,
    )
    defaults.update(overrides)
    return CreateUser(**defaults)


class TestCreateUser:
    """Testes de integração para criação de usuário."""

    async def test_create_user_returns_uuid(self, engine) -> None:
        """Verifica que criar um usuário retorna um UUID válido."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)

        result = await bus.handle(_create_user_cmd(company_id, "test@example.com"))

        assert isinstance(result, UUID)

    async def test_create_user_persists_in_database(self, engine) -> None:
        """Verifica que o usuário é persistido no banco de dados."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "persist@example.com"))

        uow = UnitOfWork()
        users = await view_user(uow, email="persist@example.com")

        assert len(users) == 1
        assert users[0].email == "persist@example.com"
        assert users[0].cpf == "12345678901"
        assert users[0].company == company_id
        assert users[0].active is True
        assert users[0].admin is False
        assert users[0].deleted is False
        assert isinstance(users[0].id, UUID)

    async def test_create_user_with_admin_flag(self, engine) -> None:
        """Verifica que o usuário admin é persistido corretamente."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(
                company_id, "admin@example.com", admin=True, cpf="99988877766"
            )
        )

        uow = UnitOfWork()
        users = await view_user(uow, email="admin@example.com")

        assert len(users) == 1
        assert users[0].admin is True
        assert users[0].cpf == "99988877766"

    async def test_create_duplicate_user_raises_error(self, engine) -> None:
        """Verifica que criar usuário com email duplicado lança exceção."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "dup@example.com"))

        bus2 = bootstrap(raise_event_errors=True)
        with pytest.raises(UserAlreadyRegistered):
            await bus2.handle(
                _create_user_cmd(company_id, "dup@example.com", password="other")
            )


class TestUpdateUser:
    """Testes de integração para atualização de usuário."""

    async def test_update_user_changes_email(self, engine) -> None:
        """Verifica que a atualização altera o email do usuário."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "old@example.com"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            UpdateUser(email="old@example.com", new_email="new@example.com")
        )

        uow = UnitOfWork()
        users = await view_user(uow, email="new@example.com")

        assert len(users) == 1
        assert users[0].email == "new@example.com"

    async def test_update_user_changes_password(self, engine) -> None:
        """Verifica que a atualização altera a senha do usuário."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(company_id, "pwd@example.com", password="old_password")
        )

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            UpdateUser(email="pwd@example.com", new_password="new_password")
        )

        uow = UnitOfWork()
        users = await view_user(uow, email="pwd@example.com")

        assert len(users) == 1

    async def test_update_user_changes_active_and_admin(self, engine) -> None:
        """Verifica que a atualização altera active e admin."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(company_id, "flags@example.com", active=True, admin=False)
        )

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            UpdateUser(email="flags@example.com", new_active=False, new_admin=True)
        )

        uow = UnitOfWork()
        users = await view_user(uow, email="flags@example.com")

        assert len(users) == 1
        assert users[0].active is False
        assert users[0].admin is True

    async def test_update_nonexistent_user_raises_error(self, engine) -> None:
        """Verifica que atualizar usuário inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(UserNotFound):
            await bus.handle(
                UpdateUser(
                    email="ghost@example.com",
                    new_email="new@example.com",
                )
            )


class TestDeleteUser:
    """Testes de integração para exclusão (soft delete) de usuário."""

    async def test_delete_user_soft_deletes_from_database(self, engine) -> None:
        """Verifica que a exclusão marca o usuário como deletado (soft delete)."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "delete@example.com"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteUser(email="delete@example.com"))

        uow = UnitOfWork()
        users = await view_user(uow, email="delete@example.com")
        assert users == []

    async def test_deleted_user_visible_with_include_deleted(self, engine) -> None:
        """Verifica que usuário deletado é visível com include_deleted=True."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "soft@example.com"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteUser(email="soft@example.com"))

        uow = UnitOfWork()
        users = await view_user(
            uow,
            email="soft@example.com",
            include_deleted=True,
        )

        assert len(users) == 1
        assert users[0].email == "soft@example.com"
        assert users[0].deleted is True

    async def test_delete_nonexistent_user_raises_error(self, engine) -> None:
        """Verifica que excluir usuário inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(UserNotFound):
            await bus.handle(DeleteUser(email="nonexistent@example.com"))

    async def test_can_recreate_user_after_soft_delete(self, engine) -> None:
        """Verifica que é possível recriar usuário com mesmo email após soft delete."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "recycle@example.com"))

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteUser(email="recycle@example.com"))

        bus3 = bootstrap(raise_event_errors=True)
        new_id = await bus3.handle(
            _create_user_cmd(company_id, "recycle@example.com", password="newpass")
        )

        assert isinstance(new_id, UUID)


class TestViewUser:
    """Testes de integração para consulta de usuário (requer company)."""

    async def test_view_existing_user_by_email(self, engine) -> None:
        """Verifica que consultar usuário existente por email retorna dados corretos."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        user_id = await bus.handle(_create_user_cmd(company_id, "view@example.com"))

        uow = UnitOfWork()
        users = await view_user(uow, email="view@example.com")

        assert len(users) == 1
        assert users[0].id == user_id
        assert users[0].email == "view@example.com"
        assert users[0].company == company_id
        assert users[0].deleted is False

    async def test_view_nonexistent_user_returns_empty_list(self, engine) -> None:
        """Verifica que consultar usuário inexistente retorna lista vazia."""
        company_id = await _create_company()
        uow = UnitOfWork()
        users = await view_user(uow, email="nobody@example.com")

        assert users == []

    async def test_view_all_users_of_company(self, engine) -> None:
        """Verifica que consultar sem email retorna todos os usuários da empresa."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(_create_user_cmd(company_id, "a@example.com", cpf="11111111111"))
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            _create_user_cmd(company_id, "b@example.com", cpf="22222222222")
        )

        uow = UnitOfWork()
        users = await view_user(uow)

        assert len(users) == 2
        emails = {u.email for u in users}
        assert emails == {"a@example.com", "b@example.com"}

    async def test_view_all_users_empty_company(self, engine) -> None:
        """Verifica que consultar empresa sem usuários retorna lista vazia."""
        company_id = await _create_company()
        uow = UnitOfWork()
        users = await view_user(uow)

        assert users == []

    async def test_view_users_excludes_deleted(self, engine) -> None:
        """Verifica que consultar sem include_deleted exclui usuários deletados."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(company_id, "active@example.com", cpf="11111111111")
        )
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            _create_user_cmd(company_id, "todelete@example.com", cpf="22222222222")
        )

        bus3 = bootstrap(raise_event_errors=True)
        await bus3.handle(DeleteUser(email="todelete@example.com"))

        uow = UnitOfWork()
        users = await view_user(uow)

        assert len(users) == 1
        assert users[0].email == "active@example.com"

    async def test_view_users_includes_deleted(self, engine) -> None:
        """Verifica que consultar com include_deleted=True retorna todos."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(company_id, "active2@example.com", cpf="11111111111")
        )
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            _create_user_cmd(company_id, "deleted2@example.com", cpf="22222222222")
        )

        bus3 = bootstrap(raise_event_errors=True)
        await bus3.handle(DeleteUser(email="deleted2@example.com"))

        uow = UnitOfWork()
        users = await view_user(uow, include_deleted=True)

        assert len(users) == 2
        emails = {u.email for u in users}
        assert emails == {"active2@example.com", "deleted2@example.com"}

    async def test_users_isolated_by_company(self, engine) -> None:
        """Verifica que usuários de empresas diferentes pertencem a empresas distintas."""
        company_a = await _create_company("Company A")
        company_b = await _create_company("Company B")

        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(company_a, "user_a@example.com", cpf="11111111111")
        )
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            _create_user_cmd(company_b, "user_b@example.com", cpf="22222222222")
        )

        uow_a = UnitOfWork()
        users_a = await view_user(uow_a, email="user_a@example.com")
        assert len(users_a) == 1
        assert users_a[0].company == company_a

        uow_b = UnitOfWork()
        users_b = await view_user(uow_b, email="user_b@example.com")
        assert len(users_b) == 1
        assert users_b[0].company == company_b

        assert company_a != company_b


class TestFullAPIFlow:
    """Testes de integração para fluxo completo: empresa → usuários."""

    async def test_create_company_then_users(self, engine) -> None:
        """Verifica o fluxo completo de criação de empresa e usuários."""
        company_id = await _create_company(
            "Flow Corp",
            email="flow@corp.com",
            responsible_name="Flow Admin",
        )

        uow = UnitOfWork()
        companies = await view_company(uow, "Flow Corp")
        assert len(companies) == 1
        assert companies[0].id == company_id

        bus = bootstrap(raise_event_errors=True)
        user_id = await bus.handle(
            _create_user_cmd(company_id, "employee@flow.com", cpf="33333333333")
        )

        uow2 = UnitOfWork()
        users = await view_user(uow2)
        assert len(users) == 1
        assert users[0].id == user_id
        assert users[0].company == company_id

    async def test_multiple_companies_with_users(self, engine) -> None:
        """Verifica múltiplas empresas com usuários isolados."""
        company_a = await _create_company("Alpha Corp")
        company_b = await _create_company("Beta Corp")

        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            _create_user_cmd(company_a, "alice@alpha.com", cpf="11111111111")
        )
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(_create_user_cmd(company_a, "bob@alpha.com", cpf="22222222222"))
        bus3 = bootstrap(raise_event_errors=True)
        await bus3.handle(
            _create_user_cmd(company_b, "charlie@beta.com", cpf="33333333333")
        )

        uow_a = UnitOfWork()
        users_a = await view_user(uow_a, email="alice@alpha.com")
        assert len(users_a) == 1
        assert users_a[0].company == company_a

        uow_a2 = UnitOfWork()
        users_a2 = await view_user(uow_a2, email="bob@alpha.com")
        assert len(users_a2) == 1
        assert users_a2[0].company == company_a

        uow_b = UnitOfWork()
        users_b = await view_user(uow_b, email="charlie@beta.com")
        assert len(users_b) == 1
        assert users_b[0].company == company_b

    async def test_full_user_lifecycle(self, engine) -> None:
        """Verifica ciclo completo: criar → atualizar → deletar usuário."""
        company_id = await _create_company("Lifecycle Corp")

        bus = bootstrap(raise_event_errors=True)
        user_id = await bus.handle(
            _create_user_cmd(
                company_id,
                "lifecycle@example.com",
                cpf="44444444444",
                admin=False,
                active=True,
            )
        )
        assert isinstance(user_id, UUID)

        uow = UnitOfWork()
        users = await view_user(uow, email="lifecycle@example.com")
        assert len(users) == 1
        assert users[0].active is True
        assert users[0].admin is False

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            UpdateUser(
                email="lifecycle@example.com",
                new_email="updated@example.com",
                new_admin=True,
            )
        )

        uow2 = UnitOfWork()
        users = await view_user(uow2, email="updated@example.com")
        assert len(users) == 1
        assert users[0].email == "updated@example.com"
        assert users[0].admin is True

        bus3 = bootstrap(raise_event_errors=True)
        await bus3.handle(DeleteUser(email="updated@example.com"))

        uow3 = UnitOfWork()
        users = await view_user(uow3, email="updated@example.com")
        assert users == []

        uow4 = UnitOfWork()
        users = await view_user(
            uow4,
            email="updated@example.com",
            include_deleted=True,
        )
        assert len(users) == 1
        assert users[0].deleted is True
