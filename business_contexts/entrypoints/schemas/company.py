"""Módulo de schemas de entrada/saída para Company."""

from uuid import UUID

from pydantic import BaseModel


class CreateCompanySchema(BaseModel):
    """Schema para criação de empresa."""

    legal_name: str
    responsible_name: str
    email: str
    cpf: str
    password: str
    active: bool = True
    trade_name: str | None = None
    cnpj: str | None = None


class UpdateCompanySchema(BaseModel):
    """Schema para atualização de empresa."""

    legal_name: str
    new_legal_name: str | None = None
    new_trade_name: str | None = None
    new_responsible_name: str | None = None
    new_email: str | None = None
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
    deleted: bool
