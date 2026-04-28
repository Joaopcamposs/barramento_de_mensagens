"""Módulo de schemas de entrada/saída para User."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateUserSchema(BaseModel):
    """Schema para criação de usuário."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    cpf: str = Field(min_length=11, max_length=14)
    active: bool
    admin: bool


class UpdateUserSchema(BaseModel):
    """Schema para atualização de usuário."""

    new_email: EmailStr | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    new_cpf: str | None = Field(default=None, min_length=11, max_length=14)
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
