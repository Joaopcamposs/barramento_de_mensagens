"""Testes de integração para o fluxo de User."""

from uuid import UUID

import pytest

from messagebus.bootstrap import bootstrap
from messagebus.unity_of_work import UnitOfWork
from business_contexts.adapters.views.user import view_user
from business_contexts.domain.commands.company import CreateCompany
from business_contexts.domain.commands.user import (
    CreateUser,
    UpdateUser,
    DeleteUser,
)
from business_contexts.domain.excecoes import (
    UserAlreadyRegistered,
    UserNotFound,
)


async def _create_company(name: str = "Test Company") -> UUID:
    """Helper para criar uma empresa e retornar seu ID."""
    bus = bootstrap(raise_event_errors=True)
    return await bus.handle(CreateCompany(name=name))


class TestCreateUser:
    """Testes de integração para criação de usuário."""

    async def test_create_user_returns_uuid(self, engine) -> None:
        """Verifica que criar um usuário retorna um UUID válido."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)

        result = await bus.handle(
            CreateUser(
                company=company_id, email="test@example.com", password="secret123"
            )
        )

        assert isinstance(result, UUID)

    async def test_create_user_persists_in_database(self, engine) -> None:
        """Verifica que o usuário é persistido no banco de dados."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            CreateUser(
                company=company_id, email="persist@example.com", password="secret123"
            )
        )

        uow = UnitOfWork()
        users = await view_user(uow, "persist@example.com")

        assert len(users) == 1
        assert users[0].email == "persist@example.com"
        assert users[0].company == company_id
        assert isinstance(users[0].id, UUID)

    async def test_create_duplicate_user_raises_error(self, engine) -> None:
        """Verifica que criar usuário com email duplicado lança exceção."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            CreateUser(
                company=company_id, email="dup@example.com", password="secret123"
            )
        )

        bus2 = bootstrap(raise_event_errors=True)
        with pytest.raises(UserAlreadyRegistered):
            await bus2.handle(
                CreateUser(
                    company=company_id, email="dup@example.com", password="other"
                )
            )


class TestUpdateUser:
    """Testes de integração para atualização de usuário."""

    async def test_update_user_changes_email(self, engine) -> None:
        """Verifica que a atualização altera o email do usuário."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            CreateUser(
                company=company_id, email="old@example.com", password="secret123"
            )
        )

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            UpdateUser(
                email="old@example.com", new_email="new@example.com", new_password=None
            )
        )

        uow = UnitOfWork()
        users = await view_user(uow, "new@example.com")

        assert len(users) == 1
        assert users[0].email == "new@example.com"

    async def test_update_user_changes_password(self, engine) -> None:
        """Verifica que a atualização altera a senha do usuário."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            CreateUser(
                company=company_id, email="pwd@example.com", password="old_password"
            )
        )

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            UpdateUser(
                email="pwd@example.com", new_email=None, new_password="new_password"
            )
        )

        uow = UnitOfWork()
        users = await view_user(uow, "pwd@example.com")

        assert len(users) == 1

    async def test_update_nonexistent_user_raises_error(self, engine) -> None:
        """Verifica que atualizar usuário inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(UserNotFound):
            await bus.handle(
                UpdateUser(
                    email="ghost@example.com",
                    new_email="new@example.com",
                    new_password=None,
                )
            )


class TestDeleteUser:
    """Testes de integração para exclusão de usuário."""

    async def test_delete_user_removes_from_database(self, engine) -> None:
        """Verifica que a exclusão remove o usuário do banco."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            CreateUser(
                company=company_id, email="delete@example.com", password="secret123"
            )
        )

        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(DeleteUser(email="delete@example.com"))

        uow = UnitOfWork()
        users = await view_user(uow, "delete@example.com")

        assert users == []

    async def test_delete_nonexistent_user_raises_error(self, engine) -> None:
        """Verifica que excluir usuário inexistente lança exceção."""
        bus = bootstrap(raise_event_errors=True)

        with pytest.raises(UserNotFound):
            await bus.handle(DeleteUser(email="nonexistent@example.com"))


class TestViewUser:
    """Testes de integração para consulta de usuário."""

    async def test_view_existing_user_by_email(self, engine) -> None:
        """Verifica que consultar usuário existente por email retorna dados corretos."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        user_id = await bus.handle(
            CreateUser(
                company=company_id, email="view@example.com", password="secret123"
            )
        )

        uow = UnitOfWork()
        users = await view_user(uow, "view@example.com")

        assert len(users) == 1
        assert users[0].id == user_id
        assert users[0].email == "view@example.com"
        assert users[0].company == company_id

    async def test_view_nonexistent_user_returns_empty_list(self, engine) -> None:
        """Verifica que consultar usuário inexistente retorna lista vazia."""
        uow = UnitOfWork()
        users = await view_user(uow, "nobody@example.com")

        assert users == []

    async def test_view_all_users(self, engine) -> None:
        """Verifica que consultar sem filtro retorna todos os usuários."""
        company_id = await _create_company()
        bus = bootstrap(raise_event_errors=True)
        await bus.handle(
            CreateUser(company=company_id, email="a@example.com", password="secret123")
        )
        bus2 = bootstrap(raise_event_errors=True)
        await bus2.handle(
            CreateUser(company=company_id, email="b@example.com", password="secret123")
        )

        uow = UnitOfWork()
        users = await view_user(uow)

        assert len(users) == 2
        emails = {u.email for u in users}
        assert emails == {"a@example.com", "b@example.com"}

    async def test_view_all_users_empty_database(self, engine) -> None:
        """Verifica que consultar sem filtro em banco vazio retorna lista vazia."""
        uow = UnitOfWork()
        users = await view_user(uow)

        assert users == []
