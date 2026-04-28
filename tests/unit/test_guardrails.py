"""Testes unitários para os guardrails da suíte."""

from __future__ import annotations

from pathlib import Path

from tests.guardrails import (
    DuplicateTestName,
    MissingDocstring,
    find_duplicate_test_names,
    find_missing_docstrings,
    find_missing_docstrings_for_targets,
    format_duplicate_test_name_report,
    format_missing_docstring_report,
)


def test_find_duplicate_test_names_reports_duplicates_in_same_file(
    tmp_path: Path,
) -> None:
    """Detecta duas funções de teste com o mesmo nome no mesmo arquivo."""
    sample = tmp_path / "test_sample.py"
    sample.write_text(
        "\n".join(
            [
                "def test_example() -> None:",
                "    pass",
                "",
                "class TestGroup:",
                "    def test_example(self) -> None:",
                "        pass",
            ]
        ),
        encoding="utf-8",
    )

    duplicates = find_duplicate_test_names(tmp_path)

    assert duplicates == [
        DuplicateTestName(
            path=sample,
            name="test_example",
            lines=(1, 5),
        )
    ]


def test_find_duplicate_test_names_ignores_same_name_in_different_files(
    tmp_path: Path,
) -> None:
    """Permite reutilizar nomes de teste quando estão em arquivos diferentes."""
    first = tmp_path / "test_first.py"
    second = tmp_path / "test_second.py"
    first.write_text(
        "def test_example() -> None:\n    pass\n",
        encoding="utf-8",
    )
    second.write_text(
        "def test_example() -> None:\n    pass\n",
        encoding="utf-8",
    )

    assert find_duplicate_test_names(tmp_path) == []


def test_format_duplicate_test_name_report_lists_file_lines_and_name() -> None:
    """Renderiza um relatório objetivo com arquivo, linhas e nome duplicado."""
    duplicate = DuplicateTestName(
        path=Path("tests/unit/test_sample.py"),
        name="test_example",
        lines=(10, 20),
    )

    report = format_duplicate_test_name_report([duplicate])

    assert "mesmo nome" in report
    assert "tests/unit/test_sample.py:10,20 -> test_example" in report


def test_find_missing_docstrings_reports_functions_and_methods(tmp_path: Path) -> None:
    """Detecta classes, funções e métodos sem docstring no diretório analisado."""
    sample = tmp_path / "module.py"
    sample.write_text(
        "\n".join(
            [
                "def helper() -> None:",
                "    pass",
                "",
                "class Service:",
                "    def run(self) -> None:",
                "        pass",
            ]
        ),
        encoding="utf-8",
    )

    assert find_missing_docstrings(tmp_path) == [
        MissingDocstring(path=sample, name="helper", line=1),
        MissingDocstring(path=sample, name="Service", line=4),
        MissingDocstring(path=sample, name="run", line=5),
    ]


def test_find_missing_docstrings_ignores_documented_functions(tmp_path: Path) -> None:
    """Ignora classes, funções e métodos que já possuem docstring."""
    sample = tmp_path / "module.py"
    sample.write_text(
        "\n".join(
            [
                "def helper() -> None:",
                '    """Doc."""',
                "    pass",
                "",
                "class Service:",
                '    """Doc."""',
                "    def run(self) -> None:",
                '        """Doc."""',
                "        pass",
            ]
        ),
        encoding="utf-8",
    )

    assert find_missing_docstrings(tmp_path) == []


def test_find_missing_docstrings_for_targets_filters_by_name_prefix(
    tmp_path: Path,
) -> None:
    """Detecta somente alvos cujo nome começa com o prefixo informado."""
    sample = tmp_path / "test_sample.py"
    sample.write_text(
        "\n".join(
            [
                "def helper() -> None:",
                "    pass",
                "",
                "def test_example() -> None:",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    assert find_missing_docstrings_for_targets(tmp_path, name_prefix="test_") == [
        MissingDocstring(path=sample, name="test_example", line=4),
    ]


def test_format_missing_docstring_report_lists_file_line_and_name() -> None:
    """Renderiza um relatório objetivo com arquivo, linha e nome sem docstring."""
    missing = MissingDocstring(
        path=Path("business_contexts/services/sample.py"),
        name="helper",
        line=12,
    )

    report = format_missing_docstring_report([missing])

    assert "sem docstring" in report
    assert "business_contexts/services/sample.py:12 -> helper" in report
