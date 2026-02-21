"""Testes complementares do domínio Company."""

import uuid7

from business_contexts.domain.aggregate.company import Company
from business_contexts.domain.commands.company import CreateCompany


class TestCompanyAggregateExtraPaths:
    """Testes de caminhos adicionais do agregado Company."""

    def test_first_company_id_property_and_no_user_creation_branch(self) -> None:
        """Retorna first_company_id e encerra cedo quando should_create_user=False."""
        first_id = uuid7.create()
        company = Company.create_aggregate(
            legal_name="Acme",
            trade_name=None,
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
            _first_company_id=first_id,
        )

        company.create(password="secret", should_create_user=False)

        assert company.first_company_id == first_id
        assert len(company.events) == 1

    def test_create_company_command_exposes_first_company_id_property(self) -> None:
        """Expõe o identificador inicial via propriedade do comando."""
        first_id = uuid7.create()
        command = CreateCompany(
            legal_name="Acme",
            responsible_name="John",
            active=True,
            cpf="12345678901",
            email="john@example.com",
            password="secret",
            _first_company_id=first_id,
        )

        assert command.first_company_id == first_id
