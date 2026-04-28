"""Módulo do Unit of Work para gerenciamento de transações."""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from business_contexts.domain.excecoes import CredentialsException
from messagebus.entities import DomainRepository, UserBase, ViewRepository

if TYPE_CHECKING:
    from business_contexts.domains import Domain
    from messagebus.messagebus import Event


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
    read_session: AsyncSession | None
    user: UserBase | None
    schema: str | None
    create_schema: bool = False
    events_without_aggregate: list[Event]

    def __init__(
        self,
        session_factory: Callable[..., Any],
        user: UserBase | None = None,
        schema: str | None = None,
        create_schema: bool = False,
    ) -> None:
        """Configura uma instancia base do UoW validando usuario/schema."""
        if (
            (user and user.company)
            and schema
            and str(user.company) != str(schema)
            and not create_schema
        ):
            raise UnitOfWorkWithProblem("The user does not belong to this schema.")

        self.sql_session_factory = session_factory
        self.user = user
        self.schema = schema or (str(self.user.company) if self.user else None)
        self.create_schema = create_schema
        self._active_context = False
        self.session = None
        self.read_session = None
        self.events_without_aggregate = []

    def __call__(
        self,
        domain: Domain | None = None,
    ) -> Self:
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

    def get_domain_repo(self, repo_type: type[WRITE_REPO]) -> WRITE_REPO:
        """Retorna o repositório de escrita configurado garantindo o tipo esperado."""
        repo = getattr(self, "domain_repo", None)
        if not isinstance(repo, repo_type):
            raise TypeError(
                f"Configured domain repo is not an instance of {repo_type.__name__}."
            )
        return repo

    def get_view_repo(self, repo_type: type[READ_REPO]) -> READ_REPO:
        """Retorna o repositório de leitura configurado garantindo o tipo esperado."""
        repo = getattr(self, "view_repo", None)
        if not isinstance(repo, repo_type):
            raise TypeError(
                f"Configured view repo is not an instance of {repo_type.__name__}."
            )
        return repo

    async def __aenter__(self) -> Self:
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

        if self.session is not None:
            await self.session.close()
        self.session = None

    @property
    def user_id(self) -> UUID | None:
        """Retorna o ID do usuário autenticado ou None se não houver usuário."""
        return self.user.id if self.user else None

    async def commit(self) -> None:
        """Confirma todas as alterações na sessão."""
        if self.session is None:
            raise RuntimeError("Unit of work session is not initialized.")
        await self.session.commit()
        self.committed = True

    async def rollback(self) -> None:
        """Desfaz todas as alterações pendentes."""
        if self.session is None:
            return
        await self.session.rollback()

    def add_events_without_aggregate(self, event: Event) -> None:
        """Adiciona um evento que não pertence a nenhum agregado específico para ser processado posteriormente."""
        self.events_without_aggregate.append(event)

    def collect_new_events(self) -> Generator[Event, None, None]:
        """
        Coleta eventos pendentes de todos os agregados rastreados.

        Yields:
            Eventos pendentes de processamento.
        """
        if hasattr(self, "domain_repo") and self.domain_repo:
            for aggregate in getattr(self.domain_repo, "seen", set()):
                while getattr(aggregate, "events", []):
                    yield aggregate.events.pop(0)

        if hasattr(self, "events_without_aggregate"):
            while self.events_without_aggregate:
                yield self.events_without_aggregate.pop(0)


WRITE_REPO = TypeVar("WRITE_REPO", bound=DomainRepository)
READ_REPO = TypeVar("READ_REPO", bound=ViewRepository)


class UnitOfWork(AbstractUnitOfWork, Generic[WRITE_REPO, READ_REPO]):
    """Implementação concreta do Unit of Work com sessões SQLAlchemy."""

    domain_repo: DomainRepository
    view_repo: ViewRepository

    def __init__(
        self,
        session_factory: Callable[..., Any] | None = None,
        user: UserBase | None = None,
        schema: str | None = None,
        create_schema: bool = False,
        read_only: bool = False,
    ) -> None:
        """Inicializa o UoW concreto definindo factories e configuracoes extras."""
        self.read_only = read_only

        # dependencias de infra
        sql_session_factory = session_factory
        if not sql_session_factory:
            from infra.database import default_async_sql_session_factory

            sql_session_factory = default_async_sql_session_factory

        self.create_full_schema_within_transaction = None
        if create_schema:
            from infra.database.schema_handlers import (
                create_full_schema_within_transaction,
            )

            self.create_full_schema_within_transaction = (
                create_full_schema_within_transaction
            )

        super().__init__(
            session_factory=sql_session_factory,
            user=user,
            schema=schema,
            create_schema=create_schema,
        )

    async def __aenter__(self) -> Self:
        """Entra no contexto, criando sessões de leitura e escrita."""
        self.committed = False

        if self.read_only:
            self.session = None
            self.read_session = await self.sql_session_factory(
                read_only=True, schema=self.schema
            )
        elif self.create_schema:
            self.session = await self.create_full_schema_within_transaction(
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

        if not self.read_only and getattr(self, "domain_repo", None) is not None:
            self.domain_repo = self.domain_repo(self.session)

        if getattr(self, "view_repo", None) is not None:
            self.view_repo = self.view_repo(self.read_session)

        return await super().__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        """Sai do contexto, fechando sessões de leitura e escrita."""
        if self.read_session is not None:
            await self.read_session.close()
            self.read_session = None

        await super().__aexit__(*args)

    def require_user_id(self: UnitOfWork) -> UUID:
        """Garante que o contexto possui um usuario autenticado."""
        if self.user_id is None:
            raise CredentialsException()
        return self.user_id
