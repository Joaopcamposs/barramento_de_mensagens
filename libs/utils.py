from collections.abc import Callable
from datetime import date, datetime
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

SerializableValue = str | int | float | dict[Any, Any] | list[Any]
T = TypeVar("T")


def serializador(
    valor: datetime
    | date
    | UUID
    | list[Any]
    | dict[Any, Any]
    | Enum
    | SerializableValue
    | None,
) -> SerializableValue:
    """Converte valores comuns de domínio para estruturas serializáveis."""
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, UUID):
        return str(valor)
    if isinstance(valor, Enum):
        valor_enum = valor.value
        if not isinstance(valor_enum, (int, float, str)):
            return serializador(valor_enum)
        return valor_enum
    if isinstance(valor, list):
        return [serializador(v) for v in valor]
    if isinstance(valor, dict):
        return {k: serializador(v) for k, v in valor.items()}
    if valor is None:
        return {}
    return valor


def serialize_if_not_none(
    value: T | None, serializer: Callable[[T], Any] = str
) -> Any | None:
    """Aplica o serializer ao valor se não for None."""
    return serializer(value) if value is not None else None


def is_public_schema(schema: str) -> bool:
    """Retorna True quando o schema for o public."""
    return schema == "public"
