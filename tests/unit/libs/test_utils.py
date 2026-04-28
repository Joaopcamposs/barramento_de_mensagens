"""Testes unitários para helpers utilitários."""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from libs.utils import is_public_schema, serializador, serialize_if_not_none


class DemoEnum(Enum):
    """Enum de apoio para validar serialização."""

    VALUE = "value"
    COMPLEX = {"nested": date(2024, 1, 2)}


def test_serializador_converts_common_values() -> None:
    """Serializa datas, UUIDs, enums e estruturas aninhadas."""
    uid = UUID("00000000-0000-0000-0000-000000000001")
    value = {
        "date": date(2024, 1, 2),
        "datetime": datetime(2024, 1, 2, 3, 4, 5),
        "uuid": uid,
        "enum": DemoEnum.VALUE,
        "nested": [DemoEnum.COMPLEX],
    }

    assert serializador(value) == {
        "date": "2024-01-02",
        "datetime": "2024-01-02T03:04:05",
        "uuid": str(uid),
        "enum": "value",
        "nested": [{"nested": "2024-01-02"}],
    }


def test_serializador_converts_none_to_empty_dict() -> None:
    """Converte None para dicionário vazio por compatibilidade."""
    assert serializador(None) == {}


def test_serializador_returns_primitive_values() -> None:
    """Retorna valores primitivos já serializáveis sem alteração."""
    assert serializador("texto") == "texto"
    assert serializador(10) == 10


def test_serialize_if_not_none_only_serializes_present_values() -> None:
    """Aplica o serializer apenas quando há valor."""
    assert serialize_if_not_none(123, serializer=lambda value: f"id-{value}") == "id-123"
    assert serialize_if_not_none(None) is None


def test_is_public_schema_matches_only_public() -> None:
    """Identifica apenas o schema public como público."""
    assert is_public_schema("public") is True
    assert is_public_schema("tenant") is False
