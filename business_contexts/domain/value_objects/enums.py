"""Módulo de enums para strings hardcoded do sistema de auditoria e entidades.

Este módulo centraliza todas as strings constantes utilizadas no sistema,
garantindo type safety e evitando erros de digitação.
"""

from enum import StrEnum


class AuditOperation(StrEnum):
    """Tipos de operações de auditoria suportadas.

    Valores:
        CREATE: Operação de criação de entidade
        UPDATE: Operação de atualização de entidade
        DELETE: Operação de exclusão de entidade
    """

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class EntityType(StrEnum):
    """Tipos de entidades auditáveis do sistema.

    Valores:
        COMPANY: Entidade de empresa
        USER: Entidade de usuário
        AUDIT_LOG: Entidade de log de auditoria
    """

    COMPANY = "Company"
    USER = "User"
    AUDIT_LOG = "AuditLog"


class AuditConstant:
    """Constantes utilizadas no sistema de auditoria.

    Esta classe contém valores fixos que não são enums mas são
    utilizados consistentemente no sistema de auditoria.
    """

    REDACTED_PASSWORD = "[REDACTED]"
