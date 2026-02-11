"""Módulo do repositório de consulta de Company."""

from sqlalchemy import select

from messagebus.entities import ViewRepository
from business_contexts.domain.aggregate.company import Company as CompanyAggregate
from business_contexts.domain.entitites.company import Company


class CompanyViewRepo(ViewRepository):
    """Repositório de consulta para Company."""

    async def get_by_name(self, name: str) -> Company | None:
        """
        Busca uma empresa pelo nome (somente leitura).

        Args:
            name: Nome da empresa.

        Returns:
            Entidade Company ou None se não encontrada.
        """
        async with self.session as session:
            company = (
                await session.execute(
                    select(CompanyAggregate).where(
                        CompanyAggregate.name == name,
                    )
                )
            ).scalar_one_or_none()
            if not company:
                return None

            entity = Company(
                id=company.id,
                name=company.name,
            )

        return entity

    async def get_all(self) -> list[Company]:
        """
        Busca todas as empresas (somente leitura).

        Returns:
            Lista de entidades Company.
        """
        async with self.session as session:
            companies = (await session.execute(select(CompanyAggregate))).scalars()
            if not companies:
                return []

            return [
                Company(
                    id=company.id,
                    name=company.name,
                )
                for company in companies
            ]
