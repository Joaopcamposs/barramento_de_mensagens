"""Módulo do Unit of Work para gerenciamento de transações."""

from __future__ import annotations

from abc import ABC
from collections.abc import Generator
from typing import Any, Generic, TypeVar, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database.schema_handlers import create_full_schema_within_transaction
from messagebus.entities import UserBase, DomainRepository, ViewRepository
from infra.database import DEFAULT_ASYNC_SQL_SESSION_FACTORY

if TYPE_CHECKING:
    from messagebus.messagebus import Event
    from messagebus.domains import Domain


class UnitOfWorkContextAlreadyOpen(Exception):
    """Exceção lançada ao tentar abrir um contexto de UoW já aberto."""

    pass


class UnitOfWorkWithProblem(Exception):
    """Exceção lançada ao tentar abrir um contexto de UoW com usuario não pertencendo ao schema."""

    pass


class AbstractUnitOfWork(ABC):
    """Interface abstrata do Unit of Work."""

    domain_repo: DomainRepository
    view_repo: ViewRepository
    seen: set
    committed: bool
    session: AsyncSession | None
    user: UserBase | None
    schema: str | None
    create_schema: bool = False

    def __init__(
        self,
        session_factory: AsyncSession = DEFAULT_ASYNC_SQL_SESSION_FACTORY,
        user: UserBase | None = None,
        schema: str | None = None,
        create_schema: bool = False,
    ) -> None:
        if (
            (user and user.company)
            and schema
            and str(user.company) != str(schema)
            and not create_schema
        ):
            raise UnitOfWorkWithProblem("The user does not belong to this schema.")

        self.sql_session_factory = session_factory or DEFAULT_ASYNC_SQL_SESSION_FACTORY
        self.user = user
        self.schema = schema
        self.create_schema = create_schema
        self._active_context = False

    def __call__(
        self,
        domain: "Domain" | None = None,  # type: ignore
    ) -> AbstractUnitOfWork:
        """
        Configura os repositórios baseado no domínio.

        Args:
            domain: Enum do domínio contendo classes de repositório.

        Returns:
            A própria instância para permitir encadeamento.
        """
        if domain:
            self.domain_repo = domain.value[0]
            self.view_repo = domain.value[1]
        return self

    async def __aenter__(self) -> AbstractUnitOfWork:
        """Entra no contexto da unidade de trabalho."""
        self.committed = False

        if self._active_context:
            raise UnitOfWorkContextAlreadyOpen()

        self._active_context = True
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Sai do contexto da unidade de trabalho."""
        self._active_context = False

        if not self.committed:
            await self.rollback()

        await self.session.close()
        await self.session.bind.dispose()
        self.session = None

    async def commit(self) -> None:
        """Confirma todas as alterações na sessão."""
        await self.session.commit()
        self.committed = True

    async def rollback(self) -> None:
        """Desfaz todas as alterações pendentes."""
        await self.session.rollback()

    def collect_new_events(self) -> Generator["Event", None, None]:
        """
        Coleta eventos pendentes de todos os agregados rastreados.

        Yields:
            Eventos pendentes de processamento.
        """
        if hasattr(self, "domain_repo") and self.domain_repo:
            for aggregate in getattr(self.domain_repo, "seen", set()):
                while getattr(aggregate, "events", []):
                    yield aggregate.events.pop(0)


WRITE_REPO = TypeVar("WRITE_REPO")
READ_REPO = TypeVar("READ_REPO")


class UnitOfWork(AbstractUnitOfWork, Generic[WRITE_REPO, READ_REPO]):
    """Implementação concreta do Unit of Work com sessões SQLAlchemy."""

    domain_repo: DomainRepository
    view_repo: ViewRepository

    def __init__(
        self,
        user: UserBase | None = None,
        schema: str | None = None,
        create_schema: bool = False,
        read_only: bool = False,
    ) -> None:
        self.read_only = read_only

        super().__init__(user=user, schema=schema, create_schema=create_schema)

    async def __aenter__(self) -> UnitOfWork:
        """Entra no contexto, criando sessões de leitura e escrita."""
        self.committed = False

        if self.create_schema:  # type: ignore[has-type]
            self.session = await create_full_schema_within_transaction(
                session_factory=self.sql_session_factory,
                schema_id=self.schema,
            )
            self.create_schema = False
        else:
            self.session = await self.sql_session_factory(
                read_only=False,
                schema=self.schema,
            )
        self.read_session = await self.sql_session_factory(
            read_only=True, schema=self.schema
        )

        if not self.read_only and self.domain_repo:
            self.domain_repo = self.domain_repo(self.session)

        if self.view_repo:
            self.view_repo = self.view_repo(self.read_session)

        return await super().__aenter__()  # type: ignore[return-value]

    async def __aexit__(  # type: ignore[override]
        self, *args: tuple[type[Exception], Exception, Exception]
    ) -> None:
        """Sai do contexto, fechando sessões de leitura e escrita."""
        if hasattr(self, "read_session") and self.read_session:
            await self.read_session.close()
            await self.read_session.bind.dispose()
            self.read_session = None

        await super().__aexit__(*args)
