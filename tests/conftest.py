from __future__ import annotations

from pathlib import Path

import pytest

from tests.guardrails import (
    find_duplicate_test_names,
    find_missing_docstrings,
    find_missing_docstrings_for_targets,
    format_duplicate_test_name_report,
    format_missing_docstring_report,
)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Falha cedo quando os guardrails estáticos encontram problemas."""
    tests_root = Path(__file__).resolve().parent
    project_root = tests_root.parent

    duplicates = find_duplicate_test_names(tests_root)
    if duplicates:
        raise pytest.UsageError(format_duplicate_test_name_report(duplicates))

    missing_docstrings = [
        *find_missing_docstrings(project_root / "business_contexts"),
        *find_missing_docstrings(project_root / "infra"),
        *find_missing_docstrings(project_root / "messagebus"),
        *find_missing_docstrings(project_root / "libs"),
        *find_missing_docstrings_for_targets(tests_root, name_prefix="test_"),
    ]
    if missing_docstrings:
        raise pytest.UsageError(format_missing_docstring_report(missing_docstrings))
