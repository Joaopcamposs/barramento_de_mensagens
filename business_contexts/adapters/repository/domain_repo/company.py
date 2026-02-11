"""Módulo do repositório de domínio de Company."""

from abc import abstractmethod
from typing import Any

from sqlalchemy import select, insert, update, delete
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
        await self._remove(company)

    @abstractmethod
    async def _remove(self, company: Company) -> None:
        """Implementação interna de remoção."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_name(self, name: str) -> Company:
        """
        Busca uma empresa pelo nome.

        Args:
            name: Nome da empresa.

        Returns:
            Agregado Company encontrado.
        """
        raise NotImplementedError()


class CompanyDomainRepo(AbstractCompanyDomainRepo):
    """Implementação concreta do repositório de domínio de Company."""

    async def create_aggregate(
        self,
        name: str,
    ) -> Company:
        """
        Cria um novo agregado Company, verificando duplicidade de nome.

        Args:
            name: Nome da empresa.

        Returns:
            Nova instância do agregado Company.

        Raises:
            CompanyAlreadyRegistered: Se já existe empresa com o mesmo nome.
        """
        async with self.session as session:
            existing_company = (
                await session.execute(select(Company).where(Company.name == name))
            ).scalar_one_or_none()
            if existing_company:
                raise CompanyAlreadyRegistered

        return Company.create_aggregate(
            name=name,
        )

    async def get_by_name(self, name: str) -> Company:
        """
        Busca uma empresa pelo nome.

        Args:
            name: Nome da empresa.

        Returns:
            Agregado Company encontrado.

        Raises:
            CompanyNotFound: Se a empresa não for encontrada.
        """
        async with self.session as session:
            company = (
                await session.execute(select(Company).where(Company.name == name))
            ).scalar_one_or_none()
            if not company:
                raise CompanyNotFound

            aggregate = Company(
                id=company.id,
                name=company.name,
            )

        return aggregate

    async def _add(
        self,
        company: Company,
    ) -> None:
        """Persiste uma empresa no banco de dados (inserção ou atualização)."""
        data = {
            "id": company.id,
            "name": company.name,
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
        """Remove uma empresa do banco de dados."""
        operation = delete(Company).where(Company.id == company.id)

        await self.session.execute(operation)
