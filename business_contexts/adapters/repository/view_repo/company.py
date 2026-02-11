"""Módulo do repositório de consulta de Company."""

from sqlalchemy import select

from messagebus.entities import ViewRepository
from business_contexts.domain.aggregate.company import Company as CompanyAggregate
from business_contexts.domain.entitites.company import Company


class CompanyViewRepo(ViewRepository):
    """Repositório de consulta para Company."""

    async def get_by_name(
        self, name: str, include_deleted: bool = False
    ) -> Company | None:
        """
        Busca uma empresa pelo nome (somente leitura).

        Args:
            name: Nome da empresa.
            include_deleted: Se True, inclui empresas deletadas.

        Returns:
            Entidade Company ou None se não encontrada.
        """
        async with self.session as session:
            query = select(CompanyAggregate).where(CompanyAggregate.name == name)
            if not include_deleted:
                query = query.where(CompanyAggregate.deleted == False)

            company = (await session.execute(query)).scalar_one_or_none()
            if not company:
                return None

            entity = Company(
                id=company.id,
                name=company.name,
                deleted=company.deleted,
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
                query = query.where(CompanyAggregate.deleted == False)

            companies = (await session.execute(query)).scalars()
            if not companies:
                return []

            return [
                Company(
                    id=company.id,
                    name=company.name,
                    deleted=company.deleted,
                )
                for company in companies
            ]
