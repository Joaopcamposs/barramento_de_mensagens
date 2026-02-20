"""Testes unitários para tipos básicos de valor."""

import pytest

from libs.basic_types import CNPJ, CPF, Email


class TestBasicTypes:
    """Testes para tipos básicos de CPF, CNPJ e Email."""

    def test_cpf_validates_and_normalizes_digits(self) -> None:
        """Normaliza CPF removendo pontuação e mantém valor em string."""
        cpf = CPF("529.982.247-25")
        assert str(cpf) == "52998224725"

    def test_cpf_invalid_raises_value_error(self) -> None:
        """Lança erro ao receber CPF inválido."""
        with pytest.raises(ValueError, match="CPF inválido"):
            CPF("11111111111")

    def test_cpf_generate_returns_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Retorna CPF gerado pelo validador externo."""
        monkeypatch.setattr(
            "libs.basic_types.CPFValidator.generate", lambda self: "12345678909"
        )
        assert CPF.generate() == "12345678909"

    def test_cnpj_new_handles_none_and_digits_only(self) -> None:
        """Retorna None para vazio e normaliza dígitos quando presente."""
        assert CNPJ(None) is None
        assert CNPJ("12.345.678/0001-90") == "12345678000190"

    def test_email_new_lowercases_or_returns_none(self) -> None:
        """Converte email para minúsculo e ignora entradas não textuais."""
        assert Email("User@Example.COM") == "user@example.com"
        assert Email.__new__(Email, 123) is None  # type: ignore[arg-type]
