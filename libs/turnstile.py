import json

import httpx
from fastapi import HTTPException, status

from libs.consts import TURNSTILE_SECRET_KEY

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, remote_ip: str | None = None) -> None:
    """
    Valida o token Turnstile com a API da Cloudflare.

    Se TURNSTILE_SECRET_KEY não estiver configurada, a validação é ignorada.
    """
    if not TURNSTILE_SECRET_KEY:
        return

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verificação captcha ausente.",
        )

    payload: dict[str, str] = {"secret": TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(TURNSTILE_VERIFY_URL, data=payload)
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha na verificação captcha.",
        ) from error

    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha na verificação captcha.",
        )

    try:
        result = response.json()
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
