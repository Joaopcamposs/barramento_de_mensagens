"""Módulo de schemas de autenticação e segurança."""

import re

from pydantic import BaseModel


class Token(BaseModel):
    """Schema de resposta contendo o token JWT."""

    access_token: str
    token_type: str
    refresh_token: str | None = None


class TokenData(BaseModel):
    """Schema de dados extraídos do token JWT."""

    username: str | None = None


class RefreshTokenRequest(BaseModel):
    """Schema de requisição para renovação de token JWT."""

    refresh_token: str


def _validate_password_complexity(password: str) -> str:
    """Valida complexidade mínima: uma maiúscula, uma minúscula e um dígito."""
    if not re.search(r"[A-Z]", password):
        raise ValueError("A senha deve conter pelo menos uma letra maiúscula")
    if not re.search(r"[a-z]", password):
        raise ValueError("A senha deve conter pelo menos uma letra minúscula")
    if not re.search(r"\d", password):
        raise ValueError("A senha deve conter pelo menos um dígito")
    return password
