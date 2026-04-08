"""Testes unitários para logger compartilhado."""

import logging

from libs.logger import logger


def test_logger_is_configured_for_messagebus() -> None:
    """Configura logger do MessageBus em nível DEBUG com propagação desativada."""
    assert logger.name == "MessageBus"
    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert logger.handlers
