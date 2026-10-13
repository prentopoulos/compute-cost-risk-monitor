"""Declared dependencies match the dev-environment spec (Phase 4 design D30).

A new dependency is a decision recorded in a design; this test makes the spec and
pyproject.toml change together.
"""

import os
import re
import tomllib
from pathlib import Path

from hypothesis import settings

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = {"altair", "duckdb", "pandas", "pytz", "streamlit"}
DEV = {
    "commitizen",
    "detect-secrets",
    "hypothesis",
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


def test_one_hypothesis_profile_locally_and_in_ci() -> None:
    # tests/conftest.py loads `gate` whether or not CI is set (Phase 6 design D11).
    current = settings()
    assert settings.get_current_profile_name() == os.environ.get(
        "HYPOTHESIS_PROFILE", "gate"
    )
    if settings.get_current_profile_name() == "gate":
        assert current.derandomize is True
        assert current.database is None
        assert current.deadline is None
