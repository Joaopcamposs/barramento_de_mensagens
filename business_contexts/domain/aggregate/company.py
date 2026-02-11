"""Módulo do agregado Company."""

from dataclasses import dataclass
from uuid import UUID

import uuid7

from business_contexts.consts import ADMIN_USER_PREFIX
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyDeleted,
    CompanyUpdated,
)
from business_contexts.domain.events.user import (
    TimeToCreateCompanyAdminUser,
    TimeToCreateInitialCompanyUser,
)
from libs.basic_types import Email
from messagebus.entities import Aggregate, OperationType


@dataclass(kw_only=True)
class Company(Aggregate):
    """Agregado que representa uma empresa no domínio."""

    id: UUID
    legal_name: str
    responsible_name: str
    email: str
    cpf: str
    active: bool
    trade_name: str | None = None
    cnpj: str | None = None

    _first_company_id: UUID | None = None

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def first_company_id(self) -> UUID | None:
        return self._first_company_id

    @staticmethod
    def create_aggregate(
        legal_name: str,
        trade_name: str | None,
        responsible_name: str,
        email: str,
        cpf: str,
        cnpj: str | None,
        active: bool,
        _first_company_id: UUID | None = None,
    ) -> "Company":
        """
        Cria uma nova instância do agregado Company.

        Args:
            legal_name: Razão social da empresa.
            trade_name: Nome fantasia da empresa (opcional).
            responsible_name: Nome do responsável.
            email: Email de contato da empresa.
            cpf: CPF do responsável.
            cnpj: CNPJ da empresa (opcional).
            active: Se a empresa está ativa.
            _first_company_id: ID fixo para a primeira empresa (opcional).

        Returns:
            Nova instância de Company com ID gerado.
        """
        company_id = _first_company_id or uuid7.create()

        return Company(
            id=company_id,
            legal_name=legal_name,
            trade_name=trade_name,
            responsible_name=responsible_name,
            email=email,
            cpf=cpf,
            cnpj=cnpj,
            active=active,
            _first_company_id=_first_company_id,
        )

    def create(
        self,
        password: str,
        should_create_user: bool = True,
    ) -> None:
        """
        Marca o agregado para inserção e emite eventos de criação.

        Emite CompanyCreated e, se should_create_user for True,
        TimeToCreateInitialCompanyUser. Para empresas que não são a primeira,
        também emite TimeToCreateCompanyAdminUser.

        Args:
            user_id: ID do usuário que está criando a empresa (opcional).
            password: Senha para o usuário inicial da empresa.
            should_create_user: Se True, emite eventos para criar usuários.
        """
        self._operation_type = OperationType.INSERT

        self.add_event(
            CompanyCreated(
                id=self.id,
            )
        )

        if not should_create_user:
            return

        self.add_event(
            TimeToCreateInitialCompanyUser(
                name=self.responsible_name,
                email=self.email,
                cpf=self.cpf,
                password=password,
                active=True,
                admin=True,
                company=self.id,
            )
        )
        if self._first_company_id is None:
            admin_user_email = Email(f"{ADMIN_USER_PREFIX}@{self.id!s}.com")
            self.add_event(
                TimeToCreateCompanyAdminUser(company=self.id, email=admin_user_email)
            )

    def update(
        self,
        legal_name: str | None = None,
        trade_name: str | None = None,
        responsible_name: str | None = None,
        email: str | None = None,
        active: bool | None = None,
    ) -> None:
        """
        Atualiza os dados da empresa e emite evento de atualização.

        Args:
            legal_name: Nova razão social (opcional).
            trade_name: Novo nome fantasia (opcional).
            responsible_name: Novo nome do responsável (opcional).
            email: Novo email (opcional).
            active: Novo status de ativação (opcional).
        """
        self._operation_type = OperationType.UPDATE

        if legal_name is not None:
            self.legal_name = legal_name
        if trade_name is not None:
            self.trade_name = trade_name
        if responsible_name is not None:
            self.responsible_name = responsible_name
        if email is not None:
            self.email = email
        if active is not None:
            self.active = active

        self.add_event(
            CompanyUpdated(
                id=self.id,
            )
        )

    def delete(self) -> None:
        """Marca o agregado como deletado (soft delete) e emite evento de exclusão."""
        self._operation_type = OperationType.DELETE

        self.deleted = True

        self.add_event(
            CompanyDeleted(
                id=self.id,
            )
        )
