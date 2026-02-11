"""Módulo do repositório de domínio de Company."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import select, insert, update
from sqlalchemy.sql import Executable

from messagebus.entities import DomainRepository, OperationType
from business_contexts.domain.aggregate.company import Company
from business_contexts.domain.excecoes import (
    CompanyAlreadyRegistered,
    CompanyNotFound,
)


class AbstractCompanyDomainRepo(DomainRepository):
    """Repositório abstrato de domínio para Company."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.seen: set[Company] = set()

    async def add(self, company: Company) -> None:
        """
        Adiciona uma empresa ao repositório e à lista de rastreados.

        Args:
            company: Agregado Company a ser adicionado.
        """
        self.seen.add(company)
        await self._add(company)

    @abstractmethod
    async def _add(self, company: Company) -> None:
        """Implementação interna de adição."""
        raise NotImplementedError

    async def remove(self, company: Company) -> None:
        """
        Remove uma empresa do repositório.

        Args:
            company: Agregado Company a ser removido.
        """
        self.seen.add(company)
        await self._remove(company)

    @abstractmethod
    async def _remove(self, company: Company) -> None:
        """Implementação interna de remoção."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_legal_name(self, legal_name: str) -> Company:
        """
        Busca uma empresa pela razão social.

        Args:
            legal_name: Razão social da empresa.

        Returns:
            Agregado Company encontrado.
        """
        raise NotImplementedError()


class CompanyDomainRepo(AbstractCompanyDomainRepo):
    """Implementação concreta do repositório de domínio de Company."""

    @staticmethod
    async def validate_company_email(email: str) -> None:
        """Valida se o email já está em uso por outra empresa."""
        from infra.database import validate_company_email

        await validate_company_email(email)

    async def create_aggregate(
        self,
        legal_name: str,
        trade_name: str | None,
        responsible_name: str,
        email: str,
        cpf: str,
        cnpj: str | None,
        active: bool,
        _first_company_id: UUID | None = None,
    ) -> Company:
        """
        Cria um novo agregado Company, verificando duplicidade de razão social.

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
            Nova instância do agregado Company.

        Raises:
            CompanyAlreadyRegistered: Se já existe empresa com a mesma razão social.
        """
        await self.validate_company_email(email)

        async with self.session as session:
            existing_company = (
                await session.execute(
                    select(Company).where(
                        Company.legal_name == legal_name,
                        Company.deleted == False,  # noqa: E712
                    )
                )
            ).scalar_one_or_none()
            if existing_company:
                raise CompanyAlreadyRegistered

        return Company.create_aggregate(
            legal_name=legal_name,
            trade_name=trade_name,
            responsible_name=responsible_name,
            email=email,
            cpf=cpf,
            cnpj=cnpj,
            active=active,
            _first_company_id=_first_company_id,
        )

    async def get_by_legal_name(self, legal_name: str) -> Company:
        """
        Busca uma empresa pela razão social.

        Args:
            legal_name: Razão social da empresa.

        Returns:
            Agregado Company encontrado.

        Raises:
            CompanyNotFound: Se a empresa não for encontrada.
        """
        async with self.session as session:
            company = (
                await session.execute(
                    select(Company).where(
                        Company.legal_name == legal_name,
                        Company.deleted == False,  # noqa: E712
                    )
                )
            ).scalar_one_or_none()
            if not company:
                raise CompanyNotFound

            aggregate = Company(
                id=company.id,
                legal_name=company.legal_name,
                trade_name=company.trade_name,
                responsible_name=company.responsible_name,
                email=company.email,
                cpf=company.cpf,
                cnpj=company.cnpj,
                active=company.active,
                deleted=company.deleted,
            )

        return aggregate

    async def _add(
        self,
        company: Company,
    ) -> None:
        """Persiste uma empresa no banco de dados (inserção ou atualização)."""
        data = {
            "id": company._first_company_id or company.id,
            "legal_name": company.legal_name,
            "trade_name": company.trade_name,
            "responsible_name": company.responsible_name,
            "email": company.email,
            "cpf": company.cpf,
            "cnpj": company.cnpj,
            "active": company.active,
            "deleted": company.deleted,
        }

        operation: Executable
        match company._operation_type:
            case OperationType.INSERT:
                operation = insert(Company).values(data)
            case OperationType.UPDATE:
                operation = update(Company).where(Company.id == company.id).values(data)
            case _:
                raise ValueError("Unsupported operation type for domain repository.")

        await self.session.execute(operation)

    async def _remove(self, company: Company) -> None:
        """Marca uma empresa como deletada no banco de dados (soft delete)."""
        operation = (
            update(Company).where(Company.id == company.id).values({"deleted": True})
        )

        await self.session.execute(operation)
