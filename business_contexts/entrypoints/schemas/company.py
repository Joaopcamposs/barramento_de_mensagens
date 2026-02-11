"""Módulo de schemas de entrada/saída para Company."""

from uuid import UUID

from pydantic import BaseModel


class CreateCompanySchema(BaseModel):
    """Schema para criação de empresa."""

    name: str


class UpdateCompanySchema(BaseModel):
    """Schema para atualização de empresa."""

    name: str
    new_name: str


class ReadCompanySchema(BaseModel):
    """Schema de leitura de empresa."""

    id: UUID
    name: str
