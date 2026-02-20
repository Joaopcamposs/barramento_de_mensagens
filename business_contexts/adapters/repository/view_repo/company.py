"""Módulo do repositório de consulta de Company."""

from sqlalchemy import select

from business_contexts.domain.aggregate.company import Company as CompanyAggregate
from business_contexts.domain.entitites.company import Company
from messagebus.entities import ViewRepository


class CompanyViewRepo(ViewRepository):
    """Repositório de consulta para Company."""

    async def get_by_legal_name(
        self, legal_name: str, include_deleted: bool = False
    ) -> Company | None:
        """
        Busca uma empresa pela razão social (somente leitura).

        Args:
            legal_name: Razão social da empresa.
            include_deleted: Se True, inclui empresas deletadas.

        Returns:
            Entidade Company ou None se não encontrada.
        """
        async with self.session as session:
            query = select(CompanyAggregate).where(
                CompanyAggregate.legal_name == legal_name
            )
            if not include_deleted:
                query = query.where(CompanyAggregate.deleted_at.is_(None))

            company = (await session.execute(query)).scalar_one_or_none()
            if not company:
                return None

            entity = Company(
                id=company.id,
                legal_name=company.legal_name,
                trade_name=company.trade_name,
                responsible_name=company.responsible_name,
                email=company.email,
                cpf=company.cpf,
                cnpj=company.cnpj,
                active=company.active,
                created_at=company.created_at,
                created_by=company.created_by,
                updated_at=company.updated_at,
                updated_by=company.updated_by,
                deleted_at=company.deleted_at,
                deleted_by=company.deleted_by,
            )

        return entity

    async def get_all(self, include_deleted: bool = False) -> list[Company]:
        """
        Busca todas as empresas (somente leitura).

        Args:
            include_deleted: Se True, inclui empresas deletadas.

        Returns:
            Lista de entidades Company.
        """
        async with self.session as session:
            query = select(CompanyAggregate)
            if not include_deleted:
                query = query.where(CompanyAggregate.deleted_at.is_(None))

            companies = (await session.execute(query)).scalars()
            if not companies:
                return []

            return [
                Company(
                    id=company.id,
                    legal_name=company.legal_name,
                    trade_name=company.trade_name,
                    responsible_name=company.responsible_name,
                    email=company.email,
                    cpf=company.cpf,
                    cnpj=company.cnpj,
                    active=company.active,
                    created_at=company.created_at,
                    created_by=company.created_by,
                    updated_at=company.updated_at,
                    updated_by=company.updated_by,
                    deleted_at=company.deleted_at,
                    deleted_by=company.deleted_by,
                )
                for company in companies
            ]
