"""Testes unitários para logger compartilhado."""

import logging

from libs.logger import fingerprint, logger


def test_logger_is_configured_for_messagebus() -> None:
    """Configura logger do MessageBus em nível DEBUG com propagação desativada."""
    assert logger.name == "MessageBus"
    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert logger.handlers


def test_fingerprint_hashes_without_exposing_value() -> None:
    """Gera hash curto determinístico para valores sensíveis."""
    value = "User@Example.com "

    result = fingerprint(value)

    assert result == fingerprint("user@example.com")
    assert result != value
    assert len(result) == 12
