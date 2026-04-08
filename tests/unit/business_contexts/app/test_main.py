"""Testes unitários do módulo principal FastAPI."""

from fastapi import FastAPI
from unittest.mock import AsyncMock

import pytest

from business_contexts.main import app, health_check, lifespan


class TestMainModule:
    """Testes para módulo principal FastAPI."""

    @pytest.mark.asyncio
    async def test_health_check_and_lifespan(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valida health check e execução do bootstrap no lifespan."""
        initializer = AsyncMock()
        monkeypatch.setattr(
            "infra.database.initializers.create_first_company_and_user", initializer
        )

        response = await health_check()
        assert response == {"message": "API is running!"}

        async with lifespan(FastAPI()):
            pass

        initializer.assert_awaited_once()

    def test_fastapi_app_is_configured_with_routes(self) -> None:
        """Confere que a aplicação global possui rotas registradas."""
        paths = {route.path for route in app.routes}
        assert "/api/health" in paths
        assert "/api/company" in paths
        assert "/api/user" in paths
        assert "/api/audit-log" in paths
        assert "/api/token" in paths
