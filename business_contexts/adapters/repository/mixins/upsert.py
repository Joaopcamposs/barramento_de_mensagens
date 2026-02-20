"""Módulo mixin para operações de upsert e soft delete em repositórios de domínio."""

from abc import ABC
from typing import Any

from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from messagebus.entities import Aggregate, OperationType


class UpsertMixin(ABC):
    """Mixin com operações genéricas de persistência para agregados.

    Fornece métodos reutilizáveis para inserção/atualização (upsert) e
    exclusão lógica (soft delete), eliminando a repetição do padrão
    match operation_type nos repositórios de domínio.
    """

    session: AsyncSession

    async def _execute_upsert(
        self,
        aggregate_class: Any,
        aggregate: Aggregate,
        data: dict,
    ) -> None:
        """
        Executa inserção ou atualização com base no tipo de operação do agregado.

        Args:
            aggregate_class: Classe do agregado (tabela ORM alvo).
            aggregate: Instância do agregado com o operation_type definido.
            data: Dicionário com os dados a serem persistidos.

        Raises:
            ValueError: Se o tipo de operação não for INSERT ou UPDATE.
        """
        match aggregate.operation_type:
            case OperationType.INSERT:
                operation = insert(aggregate_class).values(data)
            case OperationType.UPDATE:
                operation = (
                    update(aggregate_class)
                    .where(aggregate_class.id == aggregate.id)
                    .values(data)
                )
            case _:
                raise ValueError("Unsupported operation type for domain repository.")

        await self.session.execute(operation)

    async def _execute_soft_delete(
        self,
        aggregate_class: Any,
        aggregate: Aggregate,
    ) -> None:
        """
        Executa exclusão lógica (soft delete) atualizando deleted_at e deleted_by.

        Args:
            aggregate_class: Classe do agregado (tabela ORM alvo).
            aggregate: Instância do agregado com deleted_at preenchido.
        """
        operation = (
            update(aggregate_class)
            .where(aggregate_class.id == aggregate.id)
            .values(
                {
                    "deleted_at": aggregate.deleted_at,
                    "deleted_by": aggregate.deleted_by,
                }
            )
        )
        await self.session.execute(operation)
