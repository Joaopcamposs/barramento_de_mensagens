"""Módulo de inicialização da primeira empresa e usuário do sistema."""

from uuid import UUID

import uuid7

from business_contexts.adapters.orm import start_mappers
from business_contexts.bootstrap import bootstrap
from business_contexts.domain.commands.company import CreateCompany
from infra.database import delete_schema, list_existing_schemas
from libs.consts import (
    FIRST_COMPANY_ID,
    FIRST_USER_CPF,
    FIRST_USER_EMAIL,
    FIRST_USER_PASSWORD,
)
from libs.logger import logger
from messagebus.entities import UserBase


def generate_fake_user_for_first_registration(company_id: UUID) -> UserBase:
    """Gera um usuário fake para o primeiro cadastro de empresa."""
    fake_user = UserBase(
        company=company_id,
        cpf=FIRST_USER_CPF,
        email=FIRST_USER_EMAIL,
        id=uuid7.create(),
    )
    return fake_user


async def create_first_company_and_user() -> None:
    """Cria a primeira empresa e usuário do sistema, se ainda não existirem."""
    schemas = await list_existing_schemas()
    for schema in schemas:
        try:
            UUID(schema)
            return
        except ValueError:
            pass

    if not all([FIRST_COMPANY_ID, FIRST_USER_CPF, FIRST_USER_EMAIL, FIRST_USER_PASSWORD]):
        logger.warning("Bootstrap inicial ignorado: variáveis FIRST_USER_* incompletas.")
        return

    company_id = UUID(FIRST_COMPANY_ID)
    fake_user = generate_fake_user_for_first_registration(company_id)
    bus = bootstrap(user=fake_user, schema=str(company_id), create_schema=True)

    try:
        await bus.handle(
            CreateCompany(
                _first_company_id=company_id,
                legal_name="JP ADM",
                responsible_name="Admin",
                email=FIRST_USER_EMAIL,
                password=FIRST_USER_PASSWORD,
                cpf=FIRST_USER_CPF,
                active=True,
                should_create_user=True,
            )
        )
        start_mappers()
    except Exception as error:
        await delete_schema(str(company_id))
        logger.error(
            f"Erro ao criar empresa. O schema {company_id!s} foi dropado: {error}"
        )
        raise error
