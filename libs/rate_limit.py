from fastapi import Request
from slowapi import Limiter


def _get_real_ip(request: Request) -> str:
    """
    Retorna o IP real do cliente para uso no rate limiting.

    Ordem de preferência:
    1. ``Fly-Client-IP`` – injetado pela infraestrutura do Fly.io.
    2. ``CF-Connecting-IP`` – cabeçalho do proxy Cloudflare.
    3. ``X-Forwarded-For`` – primeiro IP da cadeia de proxies.
    4. ``request.client.host`` – conexão direta sem proxy.
    """
    fly_ip = request.headers.get("Fly-Client-IP")
    if fly_ip:
        return fly_ip.strip()

    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=_get_real_ip)
