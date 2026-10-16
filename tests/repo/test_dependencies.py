"""Declared dependencies match the dev-environment spec (Phase 4 design D30).

A new dependency is a decision recorded in a design; this test makes the spec and
pyproject.toml change together.
"""

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = {"altair", "anthropic", "duckdb", "pandas", "pytz", "streamlit"}
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


def _profile_under(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Load tests/conftest.py in a fresh interpreter, as pytest would, with `env`."""
    script = (
        "import runpy; runpy.run_path('tests/conftest.py');"
        " from hypothesis import settings; s = settings();"
        " print(settings.get_current_profile_name(), s.derandomize, s.database,"
        " s.deadline)"
    )
    base = {
        k: v for k, v in os.environ.items() if k not in ("CI", "HYPOTHESIS_PROFILE")
    }
    return subprocess.run(  # noqa: S603 (fixed arguments, no shell)
        [sys.executable, "-c", script],
        cwd=ROOT,
        env={**base, **env},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("env", [{}, {"CI": "true"}, {"HYPOTHESIS_PROFILE": ""}])
def test_one_hypothesis_profile_locally_and_in_ci(env: dict[str, str]) -> None:
    # Hypothesis loads its own `ci` profile when CI is set; conftest overrides it, so
    # local and CI runs generate the same examples (Phase 6 design D11).
    done = _profile_under(env)
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["gate", "True", "None", "None"]


def test_unknown_hypothesis_profile_stops_with_one_message() -> None:
    done = _profile_under({"HYPOTHESIS_PROFILE": "explor"})
    assert done.returncode != 0
    assert "HYPOTHESIS_PROFILE='explor' is not a profile here" in done.stderr


def test_only_the_drafter_imports_the_model_sdk() -> None:
    # Phase 8 design D36: the SDK is imported by drafter.py and nowhere else.
    package = ROOT / "src" / "compute_cost_risk_monitor"
    importers = {
        path.name
        for path in package.glob("*.py")
        if re.search(
            r"^\s*(import anthropic|from anthropic\b)",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    }
    assert importers <= {"drafter.py"}
