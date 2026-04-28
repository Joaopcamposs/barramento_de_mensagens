import hashlib
import logging

logger = logging.getLogger("MessageBus")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.DEBUG)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(_handler)
    logger.propagate = False


def fingerprint(value: object, *, length: int = 12) -> str:
    """Retorna um hash curto para correlacionar dados sem expor PII em logs."""
    normalized = str(value).strip().lower().encode()
    return hashlib.sha256(normalized).hexdigest()[:length]
