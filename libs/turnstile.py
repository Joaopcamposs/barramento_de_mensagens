"""Validacao de Cloudflare Turnstile para protecao contra bots."""

import json

import httpx
from fastapi import HTTPException, status

from libs.consts import TURNSTILE_SECRET_KEY

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, remote_ip: str | None = None) -> None:
    """Valida o token Turnstile com a API da Cloudflare.

    Se TURNSTILE_SECRET_KEY nao estiver configurada (dev/test), a validacao e ignorada.
    """
    if not TURNSTILE_SECRET_KEY:
        return

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verificação captcha ausente.",
        )

    payload: dict[str, str] = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha na verificação captcha.",
        ) from error

    if not resp.is_success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha na verificação captcha.",
        )

    try:
        result = resp.json()
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha na verificação captcha.",
        ) from error

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha na verificação captcha. Tente novamente.",
        )
