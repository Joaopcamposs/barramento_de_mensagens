"""Módulo de schemas de autenticação e segurança."""

from pydantic import BaseModel


class Token(BaseModel):
    """Schema de resposta contendo o token JWT."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema de dados extraídos do token JWT."""

    username: str | None = None
