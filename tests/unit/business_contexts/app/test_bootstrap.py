"""Testes unitários do bootstrap de business_contexts."""

from types import SimpleNamespace
from typing import Any

import pytest

from business_contexts import bootstrap as business_bootstrap


class TestBusinessBootstrap:
    """Testes para bootstrap do contexto de negócio."""

    def test_bootstrap_uses_default_handlers_and_creates_uow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Usa handlers padrão e instancia UnitOfWork quando não informado."""
        captured: dict[str, Any] = {}

        monkeypatch.setattr(
            business_bootstrap,
            "UnitOfWork",
            lambda **kwargs: captured.setdefault("uow", SimpleNamespace(**kwargs)),
        )
        monkeypatch.setattr(
            business_bootstrap,
            "bootstrap_base",
            lambda **kwargs: captured.setdefault("kwargs", kwargs),
        )

        result = business_bootstrap.bootstrap(
            schema="tenant", create_schema=True, read_only=True
        )

        assert result == captured["kwargs"]
        assert captured["uow"].schema == "tenant"
        assert captured["kwargs"]["raise_event_errors"] is False

    def test_bootstrap_uses_custom_handlers_and_uow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Respeita handlers e UoW customizados quando fornecidos."""
        custom_uow = object()
        custom_events = {object: []}
        custom_commands = {object: lambda *_: None}
        captured: dict[str, Any] = {}

        monkeypatch.setattr(
            business_bootstrap,
            "bootstrap_base",
            lambda **kwargs: captured.setdefault("kwargs", kwargs),
        )

        result = business_bootstrap.bootstrap(
            uow=custom_uow,  # type: ignore[arg-type]
            event_handlers=custom_events,  # type: ignore[arg-type]
            command_handlers=custom_commands,  # type: ignore[arg-type]
            raise_event_errors=True,
        )

        assert result == captured["kwargs"]
        assert captured["kwargs"]["uow"] is custom_uow
        assert captured["kwargs"]["event_handlers"] is custom_events
        assert captured["kwargs"]["command_handlers"] is custom_commands
        assert captured["kwargs"]["raise_event_errors"] is True
