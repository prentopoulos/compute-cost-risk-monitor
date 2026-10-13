"""Declared dependencies match the dev-environment spec (Phase 4 design D30).

A new dependency is a decision recorded in a design; this test makes the spec and
pyproject.toml change together.
"""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = {"altair", "duckdb", "pandas", "pytz", "streamlit"}
DEV = {
    "commitizen",
    "detect-secrets",
    "mypy",
    "pandas-stubs",
    "pytest",
    "pytest-cov",
    "pytest-socket",
    "ruff",
    "types-pytz",
}


def _names(requirements: list[str]) -> set[str]:
    return {re.split(r"[<>=!~ \[;]", item, maxsplit=1)[0] for item in requirements}


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_runtime_dependencies_match_the_spec() -> None:
    project = _project()["project"]
    assert isinstance(project, dict)
    assert _names(project["dependencies"]) == RUNTIME


def test_dev_dependencies_match_the_spec() -> None:
    groups = _project()["dependency-groups"]
    assert isinstance(groups, dict)
    assert _names(groups["dev"]) == DEV
