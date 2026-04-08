"""Testes unitários para rate limiting."""

from types import SimpleNamespace
from typing import Any

from libs.rate_limit import _get_real_ip


def _request(headers: dict[str, str], client_host: str | None = "10.0.0.1") -> Any:
    """Cria um request mínimo para exercitar a extração de IP."""
    client = SimpleNamespace(host=client_host) if client_host else None
    return SimpleNamespace(headers=headers, client=client)


def test_get_real_ip_prefers_fly_header() -> None:
    """Prioriza o cabeçalho injetado pelo Fly.io."""
    request = _request({"Fly-Client-IP": " 1.1.1.1 ", "CF-Connecting-IP": "2.2.2.2"})

    assert _get_real_ip(request) == "1.1.1.1"


def test_get_real_ip_uses_cloudflare_header() -> None:
    """Usa o cabeçalho Cloudflare quando não há Fly-Client-IP."""
    request = _request({"CF-Connecting-IP": " 2.2.2.2 "})

    assert _get_real_ip(request) == "2.2.2.2"


def test_get_real_ip_uses_first_forwarded_ip() -> None:
    """Usa o primeiro IP do X-Forwarded-For."""
    request = _request({"X-Forwarded-For": "3.3.3.3, 4.4.4.4"})

    assert _get_real_ip(request) == "3.3.3.3"


def test_get_real_ip_falls_back_to_client_or_localhost() -> None:
    """Usa o host direto ou localhost quando não há client."""
    assert _get_real_ip(_request({})) == "10.0.0.1"
    assert _get_real_ip(_request({}, client_host=None)) == "127.0.0.1"
