"""Módulo de schemas de entrada/saída para Company."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from business_contexts.entrypoints.schemas.security import (
    _validate_password_complexity,
)


class CreateCompanySchema(BaseModel):
    """Schema para criação de empresa."""

    legal_name: str = Field(min_length=1, max_length=255)
    responsible_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    cpf: str = Field(min_length=11, max_length=14)
    password: str = Field(min_length=8, max_length=128)
    active: bool = True
    trade_name: str | None = Field(default=None, max_length=255)
    cnpj: str | None = Field(default=None, min_length=14, max_length=18)

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        """Valida complexidade da senha de cadastro."""
        return _validate_password_complexity(v)


class UpdateCompanySchema(BaseModel):
    """Schema para atualização de empresa."""

    new_legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    new_trade_name: str | None = Field(default=None, min_length=1, max_length=255)
    new_responsible_name: str | None = Field(default=None, min_length=1, max_length=255)
    new_email: EmailStr | None = None
    new_active: bool | None = None


class ReadCompanySchema(BaseModel):
    """Schema de leitura de empresa."""

    id: UUID
    legal_name: str
    trade_name: str | None = None
    responsible_name: str
    email: str
    cpf: str
    cnpj: str | None = None
    active: bool
