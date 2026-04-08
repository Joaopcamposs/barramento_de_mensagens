"""Testes unitários para validação Turnstile."""

import json

import httpx
import pytest
from fastapi import HTTPException

import libs.turnstile as turnstile_module
from libs.turnstile import TURNSTILE_VERIFY_URL, verify_turnstile


class DummyResponse:
    """Resposta mínima para simular httpx."""

    def __init__(self, *, is_success: bool = True, payload: object | None = None) -> None:
        """Guarda estado HTTP e payload JSON da resposta."""
        self.is_success = is_success
        self.payload = payload if payload is not None else {"success": True}

    def json(self) -> object:
        """Retorna o payload configurado ou levanta erro de JSON."""
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class DummyAsyncClient:
    """Cliente assíncrono mínimo para simular httpx.AsyncClient."""

    response: DummyResponse | Exception = DummyResponse()
    requests: list[tuple[str, dict[str, str]]] = []

    def __init__(self, *, timeout: int) -> None:
        """Armazena o timeout recebido pelo cliente."""
        self.timeout = timeout

    async def __aenter__(self) -> "DummyAsyncClient":
        """Retorna o próprio cliente ao entrar no contexto."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Sai do contexto sem ação adicional."""
        return None

    async def post(self, url: str, data: dict[str, str]) -> DummyResponse:
        """Registra a requisição e retorna a resposta configurada."""
        self.requests.append((url, data))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture(autouse=True)
def reset_dummy_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restaura o cliente fake e a chave Turnstile entre testes."""
    DummyAsyncClient.response = DummyResponse()
    DummyAsyncClient.requests = []
    monkeypatch.setattr(turnstile_module.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(turnstile_module, "TURNSTILE_SECRET_KEY", "secret")


async def test_verify_turnstile_skips_when_secret_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ignora a validação quando a chave secreta não está configurada."""
    monkeypatch.setattr(turnstile_module, "TURNSTILE_SECRET_KEY", "")

    await verify_turnstile(token=None)

    assert DummyAsyncClient.requests == []


async def test_verify_turnstile_posts_payload_with_remote_ip() -> None:
    """Envia token, secret e IP remoto para a API da Cloudflare."""
    await verify_turnstile(token="token", remote_ip="1.1.1.1")

    assert DummyAsyncClient.requests == [
        (
            TURNSTILE_VERIFY_URL,
            {"secret": "secret", "response": "token", "remoteip": "1.1.1.1"},
        )
    ]


async def test_verify_turnstile_requires_token() -> None:
    """Falha quando a chave está configurada e o token não foi enviado."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_turnstile(token=None)

    assert exc_info.value.status_code == 400


async def test_verify_turnstile_handles_request_errors() -> None:
    """Converte erro de rede em erro HTTP 503."""
    DummyAsyncClient.response = httpx.RequestError("boom")

    with pytest.raises(HTTPException) as exc_info:
        await verify_turnstile(token="token")

    assert exc_info.value.status_code == 503


async def test_verify_turnstile_handles_unsuccessful_response() -> None:
    """Converte resposta HTTP mal sucedida em erro HTTP 503."""
    DummyAsyncClient.response = DummyResponse(is_success=False)

    with pytest.raises(HTTPException) as exc_info:
        await verify_turnstile(token="token")

    assert exc_info.value.status_code == 503


async def test_verify_turnstile_handles_invalid_json() -> None:
    """Converte JSON inválido em erro HTTP 503."""
    DummyAsyncClient.response = DummyResponse(
        payload=json.JSONDecodeError("bad", "doc", 0)
    )

    with pytest.raises(HTTPException) as exc_info:
        await verify_turnstile(token="token")

    assert exc_info.value.status_code == 503


async def test_verify_turnstile_rejects_failed_challenge() -> None:
    """Converte desafio recusado em erro HTTP 400."""
    DummyAsyncClient.response = DummyResponse(payload={"success": False})

    with pytest.raises(HTTPException) as exc_info:
        await verify_turnstile(token="token")

    assert exc_info.value.status_code == 400
