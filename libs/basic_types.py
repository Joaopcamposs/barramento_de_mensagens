"""Módulo de tipos básicos de valor para validação de documentos e dados."""

from __future__ import annotations

from validate_docbr import CPF as CPFValidator  # noqa: N811


class CPF(str):
    """Tipo de valor que representa e valida um CPF brasileiro."""

    def __init__(self, cpf: str = ""):
        """Inicializa o CPF normalizando os dígitos e acionando a validação."""
        self.cpf = self.digits_only(cpf)
        self.validate()

    def validate(self) -> None:
        """Valida o CPF usando a biblioteca validate_docbr."""
        if not CPFValidator().validate(self.cpf):
            raise ValueError("CPF inválido")

    @staticmethod
    def digits_only(cpf: str) -> str:
        """Retorna apenas os dígitos numéricos do CPF."""
        return "".join([char for char in cpf if char.isdigit()])

    @staticmethod
    def generate() -> str:
        """Gera um CPF válido aleatório."""
        generated_cpf = CPFValidator().generate()
        return str(generated_cpf)

    def __str__(self) -> str:
        """Retorna o CPF normalizado apenas com dígitos."""
        return self.cpf


class CNPJ(str):
    """Tipo de valor que representa um CNPJ, formatando apenas dígitos."""

    def __new__(cls, value: str | None) -> CNPJ | None:  # type: ignore[misc]
        """Normaliza o CNPJ informado antes de criar o valor."""
        if not value:
            return None
        if isinstance(value, str):
            value = cls.digits_only(value)
        return super().__new__(cls, value)  # type: ignore[report-arg-type]

    @staticmethod
    def digits_only(cnpj: str) -> str:
        """Retorna apenas os dígitos numéricos do CNPJ."""
        return "".join([char for char in cnpj if char.isdigit()])


class Email(str):
    """Tipo de valor que representa um email, convertendo para minúsculas."""

    def __new__(cls, value: str) -> Email | None:  # type: ignore[misc]
        """Converte o email para minúsculas ao construir o tipo valor."""
        if isinstance(value, str):
            return super().__new__(cls, value.lower())  # type: ignore[report-arg-type]
        return None
