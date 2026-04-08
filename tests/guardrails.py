"""Guardrails estáticos reutilizáveis para a suíte de testes."""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DuplicateTestName:
    """Representa um nome de teste repetido dentro do mesmo arquivo."""

    path: Path
    name: str
    lines: tuple[int, ...]


@dataclass(frozen=True)
class MissingDocstring:
    """Representa uma classe oufunção sem docstring."""

    path: Path
    name: str
    line: int


def _collect_test_names(tree: ast.Module) -> dict[str, list[int]]:
    """Coleta nomes de testes coletáveis no módulo e suas linhas."""
    collected: dict[str, list[int]] = defaultdict(list)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                collected[node.name].append(node.lineno)
            continue

        if isinstance(node, ast.ClassDef):
            for class_node in node.body:
                if isinstance(
                    class_node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and class_node.name.startswith("test_"):
                    collected[class_node.name].append(class_node.lineno)

    return collected


def _iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Lista todas as funções e métodos declarados na árvore AST."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _iter_docstring_targets(
    tree: ast.AST,
) -> list[ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef]:
    """Lista classes, funções e métodos que devem ter docstring."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def find_duplicate_test_names(root: Path) -> list[DuplicateTestName]:
    """Encontra testes com o mesmo nome declarados no mesmo arquivo."""
    duplicates: list[DuplicateTestName] = []

    for path in sorted(root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lines in _collect_test_names(tree).items():
            if len(lines) > 1:
                duplicates.append(
                    DuplicateTestName(
                        path=path,
                        name=name,
                        lines=tuple(lines),
                    )
                )

    return duplicates


def format_duplicate_test_name_report(duplicates: list[DuplicateTestName]) -> str:
    """Formata um relatório legível para nomes de testes duplicados."""
    header = "Foram encontrados testes com o mesmo nome no mesmo arquivo:"
    details = [
        f"- {duplicate.path}:{','.join(str(line) for line in duplicate.lines)} -> {duplicate.name}"
        for duplicate in duplicates
    ]
    return "\n".join([header, *details])


def find_missing_docstrings(root: Path) -> list[MissingDocstring]:
    """Encontra classes, funções e métodos sem docstring em um diretório de código."""
    return find_missing_docstrings_for_targets(root)


def find_missing_docstrings_for_targets(
    root: Path,
    name_prefix: str | None = None,
) -> list[MissingDocstring]:
    """Encontra classes, funções e métodos sem docstring, com filtro opcional por prefixo."""
    missing: list[MissingDocstring] = []

    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in _iter_docstring_targets(tree):
            if name_prefix is not None and not node.name.startswith(name_prefix):
                continue
            if ast.get_docstring(node) is not None:
                continue
            missing.append(
                MissingDocstring(
                    path=path,
                    name=node.name,
                    line=node.lineno,
                )
            )

    return missing


def format_missing_docstring_report(missing: list[MissingDocstring]) -> str:
    """Formata um relatório legível para funções sem docstring."""
    header = "Foram encontradas funções ou métodos sem docstring:"
    details = [f"- {item.path}:{item.line} -> {item.name}" for item in missing]
    return "\n".join([header, *details])
