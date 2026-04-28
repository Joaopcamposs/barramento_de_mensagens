from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import pytest

from business_contexts.main import (
    app,
    get_app_version,
    get_cors_origins,
    health_check,
    lifespan,
)


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

    def test_app_helpers_and_security_headers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valida helpers de versão/CORS e headers de segurança."""
        monkeypatch.setenv(
            "CORS_ORIGINS", "https://app.example.com, https://admin.example.com"
        )
        assert get_cors_origins() == [
            "https://app.example.com",
            "https://admin.example.com",
        ]
        assert get_app_version() == "0.0.1"

        response = TestClient(app).get("/api/health")

        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "same-origin"
