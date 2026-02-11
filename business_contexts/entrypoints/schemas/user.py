"""Módulo de schemas de entrada/saída para User."""

from uuid import UUID

from pydantic import BaseModel


class CreateUserSchema(BaseModel):
    """Schema para criação de usuário."""

    company: UUID
    email: str
    password: str


class UpdateUserSchema(BaseModel):
    """Schema para atualização de usuário."""

    email: str
    new_email: str | None = None
    new_password: str | None = None


class ReadUserSchema(BaseModel):
    """Schema de leitura de usuário."""

    id: UUID
    company: UUID
    email: str
    deleted: bool
