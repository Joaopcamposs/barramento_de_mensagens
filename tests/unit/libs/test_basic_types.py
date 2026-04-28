"""Testes unitários para tipos básicos de valor."""

import pytest

from libs.basic_types import CNPJ, CPF, Email, Phone


class TestBasicTypes:
    """Testes para tipos básicos de CPF, CNPJ, Email e Phone."""

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

    def test_phone_normalizes_digits(self) -> None:
        """Normaliza telefone removendo caracteres não numéricos."""
        assert Phone("+55 (11) 91234-5678") == "5511912345678"

    def test_phone_rejects_invalid_lengths(self) -> None:
        """Lança erro quando o telefone não tem tamanho aceito."""
        with pytest.raises(ValueError, match="Telefone inválido"):
            Phone("5511999")

    def test_phone_rejects_zero_ddi_or_ddd(self) -> None:
        """Lança erro quando DDI ou DDD têm formato inválido."""
        with pytest.raises(ValueError, match="Telefone inválido"):
            Phone("0011912345678")
        with pytest.raises(ValueError, match="Telefone inválido"):
            Phone("5501912345678")
