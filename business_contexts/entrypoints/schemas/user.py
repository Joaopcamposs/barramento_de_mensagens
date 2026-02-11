"""Módulo de schemas de entrada/saída para User."""

from uuid import UUID

from pydantic import BaseModel


class CreateUserSchema(BaseModel):
    """Schema para criação de usuário."""

    company: UUID
    email: str
    password: str
    cpf: str
    active: bool
    admin: bool


class UpdateUserSchema(BaseModel):
    """Schema para atualização de usuário."""

    company: UUID
    email: str
    new_email: str | None = None
    new_password: str | None = None
    new_cpf: str | None = None
    new_active: bool | None = None
    new_admin: bool | None = None


class ReadUserSchema(BaseModel):
    """Schema de leitura de usuário."""

    id: UUID
    company: UUID
    email: str
    cpf: str
    active: bool
    admin: bool
    deleted: bool
