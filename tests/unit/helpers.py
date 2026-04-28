"""Utilitários de teste para cenários assíncronos e doubles de infraestrutura."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


class FakeBind:
    """Double simples para bind de sessão com suporte a dispose assíncrono."""

    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        """Marca que o recurso foi descartado."""
        self.disposed = True


class FakeScalars:
    """Wrapper de resultados em estilo SQLAlchemy scalars()."""

    def __init__(self, items: Iterable[Any]) -> None:
        self._items = list(items)

    def all(self) -> list[Any]:
        """Retorna todos os itens materializados."""
        return list(self._items)

    def __iter__(self):
        return iter(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)


class FakeResult:
    """Resultado fake para operações execute()."""

    def __init__(
        self,
        scalar: Any | None = None,
        scalars: Iterable[Any] | None = None,
        fetchone: Any | None = None,
    ) -> None:
        self._scalar = scalar
        self._scalars = list(scalars or [])
        self._fetchone = fetchone

    def scalar_one_or_none(self) -> Any | None:
        """Retorna o valor escalar único ou None."""
        return self._scalar

    def scalars(self) -> FakeScalars:
        """Retorna coleção de escalares."""
        return FakeScalars(self._scalars)

    def fetchone(self) -> Any | None:
        """Simula fetchone do cursor."""
        return self._fetchone

    def __iter__(self):
        """Permite iteração direta sobre linhas escalares."""
        return iter(self._scalars)


class FakeAsyncSession:
    """Sessão assíncrona fake com suporte a contexto e operações básicas."""

    def __init__(self, execute_results: list[Any] | None = None) -> None:
        self.execute_results = list(execute_results or [])
        self.execute_calls: list[Any] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.bind = FakeBind()
        self.schema: str | None = None

    async def __aenter__(self) -> "FakeAsyncSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def execute(self, query: Any, *args: Any, **kwargs: Any) -> Any:
        """Registra a query e retorna o próximo resultado configurado."""
        self.execute_calls.append((query, args, kwargs))
        if self.execute_results:
            result = self.execute_results.pop(0)
            return result(query) if callable(result) else result
        return FakeResult()

    async def commit(self) -> None:
        """Simula commit."""
        self.committed = True

    async def rollback(self) -> None:
        """Simula rollback."""
        self.rolled_back = True

    async def close(self) -> None:
        """Simula fechamento de sessão."""
        self.closed = True


@dataclass
class FakeUser:
    """Usuário fake para testes que exigem contexto autenticado."""

    id: Any
    company: Any


class FakeUoW:
    """Unit of Work fake para handlers e views."""

    def __init__(
        self,
        domain_repo: Any = None,
        view_repo: Any = None,
        user: Any = None,
    ) -> None:
        self.domain_repo = domain_repo
        self.view_repo = view_repo
        self.user = user
        self.committed = False
        self.received_domain = None

    def __call__(self, domain: Any = None) -> "FakeUoW":
        self.received_domain = domain
        return self

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    @property
    def user_id(self) -> Any | None:
        """Retorna o id do usuário fake, quando existir."""
        return self.user.id if self.user else None

    def get_domain_repo(self, repo_type: Any) -> Any:
        """Retorna domain_repo fake, espelhando helper tipado da UoW real."""
        return self.domain_repo

    def get_view_repo(self, repo_type: Any) -> Any:
        """Retorna view_repo fake, espelhando helper tipado da UoW real."""
        return self.view_repo

    async def commit(self) -> None:
        """Simula commit da UoW."""
        self.committed = True


class FakeEngineBeginContext:
    """Context manager fake para engine.begin()."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    async def __aenter__(self) -> Any:
        return self.connection

    async def __aexit__(self, *args: Any) -> None:
        return None


class FakeConnection:
    """Conexão fake com execute e run_sync."""

    def __init__(self, execute_results: list[Any] | None = None) -> None:
        self.execute_results = list(execute_results or [])
        self.execute_calls: list[Any] = []
        self.run_sync_calls: list[Any] = []

    async def execute(self, query: Any, *args: Any, **kwargs: Any) -> Any:
        self.execute_calls.append((query, args, kwargs))
        if self.execute_results:
            result = self.execute_results.pop(0)
            return result(query) if callable(result) else result
        return FakeResult()

    async def run_sync(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        self.run_sync_calls.append((callback, args, kwargs))


class FakeEngine:
    """Engine fake com begin e execution_options."""

    def __init__(self, connection: FakeConnection | None = None) -> None:
        self.connection = connection or FakeConnection()
        self.disposed = False
        self.execution_options_calls: list[dict[str, Any]] = []

    def begin(self) -> FakeEngineBeginContext:
        return FakeEngineBeginContext(self.connection)

    def execution_options(self, **kwargs: Any) -> Any:
        self.execution_options_calls.append(kwargs)
        return SimpleNamespace(kind="bound-engine", options=kwargs)

    async def dispose(self) -> None:
        self.disposed = True
