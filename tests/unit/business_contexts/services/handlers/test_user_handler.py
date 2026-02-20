"""Testes unitários dos handlers de User."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.domain.commands.user import CreateUser, DeleteUser, UpdateUser
from business_contexts.domain.events.user import (
    TimeToCreateInitialCompanyUser,
    UserCreated,
    UserDeleted,
    UserUpdated,
)
from business_contexts.services.handlers import user as user_handlers
from tests.unit.helpers import FakeUoW


class TestUserHandlers:
    """Testes dos handlers do domínio User."""

    @pytest.mark.asyncio
    async def test_create_update_delete_user(self) -> None:
        """Cobre criação, atualização e remoção de usuário privado."""
        user = SimpleNamespace(
            id=uuid7.create(),
            create=lambda **_: None,
            update=lambda **_: None,
            delete=lambda **_: None,
        )
        domain_repo = SimpleNamespace(
            create_aggregate=AsyncMock(return_value=user),
            add=AsyncMock(),
            get_by_email=AsyncMock(return_value=user),
            remove=AsyncMock(),
        )

        uow = FakeUoW(domain_repo=domain_repo, user=SimpleNamespace(id=uuid7.create()))

        created_id = await user_handlers.create_user(
            CreateUser(
                company=uuid7.create(),
                email="user@example.com",
                cpf="12345678901",
                password="secret",
            ),
            uow,  # type: ignore[arg-type]
        )
        await user_handlers.update_user(
            UpdateUser(email="user@example.com", new_email="new@example.com"), uow
        )  # type: ignore[arg-type]
        await user_handlers.delete_user(DeleteUser(email="new@example.com"), uow)  # type: ignore[arg-type]

        assert created_id == user.id
        assert domain_repo.add.await_count == 2
        domain_repo.remove.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_accepts_event_payload(self) -> None:
        """Permite criação de usuário a partir de evento de onboarding."""
        user = SimpleNamespace(id=uuid7.create(), create=lambda **_: None)
        domain_repo = SimpleNamespace(
            create_aggregate=AsyncMock(return_value=user), add=AsyncMock()
        )
        uow = FakeUoW(domain_repo=domain_repo)

        event = TimeToCreateInitialCompanyUser(
            company=uuid7.create(),
            name="Owner",
            email="owner@example.com",
            cpf="12345678901",
            password="secret",
            active=True,
            admin=True,
        )

        result = await user_handlers.create_user(event, uow)  # type: ignore[arg-type]
        assert result == user.id

    @pytest.mark.asyncio
    async def test_user_event_handlers_log(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Registra logs ao receber eventos de usuário."""
        logs: list[str] = []
        monkeypatch.setattr(
            user_handlers.logger, "info", lambda message: logs.append(message)
        )

        uid = uuid7.create()
        company = uuid7.create()
        await user_handlers.user_created(
            UserCreated(id=uid, company=company, entity_type="User"), FakeUoW()
        )  # type: ignore[arg-type]
        await user_handlers.user_updated(
            UserUpdated(id=uid, company=company, entity_type="User"), FakeUoW()
        )  # type: ignore[arg-type]
        await user_handlers.user_deleted(
            UserDeleted(id=uid, company=company, entity_type="User"), FakeUoW()
        )  # type: ignore[arg-type]

        assert len(logs) == 3

    @pytest.mark.asyncio
    async def test_public_user_handlers(self) -> None:
        """Cobre sincronização de usuário público em criação/atualização/remoção."""
        private_user = SimpleNamespace(
            id=uuid7.create(),
            company=uuid7.create(),
            email="user@example.com",
            password_hash="hashed",
            active=True,
        )
        public_user = SimpleNamespace(
            id=private_user.id,
            register=lambda: None,
            update=lambda **_: None,
            remove=lambda: None,
        )

        domain_repo = SimpleNamespace(
            add_public_user=AsyncMock(),
            get_public_user_by_id=AsyncMock(return_value=public_user),
            remove_public_user=AsyncMock(),
        )
        view_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=private_user))
        uow = FakeUoW(domain_repo=domain_repo, view_repo=view_repo)

        original = user_handlers.PublicUser.create_registration_aggregate
        user_handlers.PublicUser.create_registration_aggregate = classmethod(
            lambda cls, user: public_user
        )

        created_id = await user_handlers.create_public_user(
            UserCreated(
                id=private_user.id, company=private_user.company, entity_type="User"
            ),
            uow,
        )  # type: ignore[arg-type]
        await user_handlers.update_public_user(
            UserUpdated(
                id=private_user.id, company=private_user.company, entity_type="User"
            ),
            uow,
        )  # type: ignore[arg-type]
        await user_handlers.remove_public_user(
            UserDeleted(
                id=private_user.id, company=private_user.company, entity_type="User"
            ),
            uow,
        )  # type: ignore[arg-type]

        user_handlers.PublicUser.create_registration_aggregate = original

        assert created_id == private_user.id
        domain_repo.add_public_user.assert_awaited()
        domain_repo.remove_public_user.assert_awaited_once()
