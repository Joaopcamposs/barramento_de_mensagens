"""Testes unitários dos endpoints de User."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.entrypoints.api import user as user_api
from business_contexts.entrypoints.schemas.user import CreateUserSchema, UpdateUserSchema


class TestUserApi:
    """Testes para endpoints de usuário."""

    @pytest.mark.asyncio
    async def test_user_crud_endpoints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cobre criação, atualização, consulta e remoção de usuário."""
        current = SimpleNamespace(id=uuid7.create(), company=uuid7.create())
        token = user_api.current_user.set(current)

        bus = SimpleNamespace(handle=AsyncMock(return_value=uuid7.create()), uow=object())

        created_id = await user_api.post_user(
            CreateUserSchema(
                email="user@example.com",
                password="secret123",
                cpf="12345678901",
                active=True,
                admin=False,
            ),
            bus=bus,
        )
        assert created_id is not None

        await user_api.put_user(
            "user@example.com", UpdateUserSchema(new_email="new@example.com"), bus=bus
        )

        monkeypatch.setattr(
            user_api, "view_user", AsyncMock(return_value=[{"id": str(created_id)}])
        )
        users = await user_api.get_user(email="user@example.com", bus=bus)
        assert users == [{"id": str(created_id)}]

        await user_api.delete_user("new@example.com", bus=bus)
        user_api.current_user.reset(token)
