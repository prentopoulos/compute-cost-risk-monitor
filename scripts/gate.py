"""Local quality gate. Run with: uv run --frozen python scripts/gate.py

Runs every check even after one fails, prints a summary, and exits non-zero if any
check failed. Tools run from the locked environment (sys.executable) or by full path,
never by a bare name from PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENSPEC_CLI = (
    ROOT / "node_modules" / "@fission-ai" / "openspec" / "bin" / "openspec.js"
)
COMMIT_RANGE = "origin/main..HEAD"
SECRETS_BASELINE = ".secrets.baseline"
SECRETS_BATCH = 100


@dataclass
class Result:
    name: str
    status: str  # "pass", "fail" or "skip"
    seconds: float
    note: str = ""


def run(argv: list[str], env: dict[str, str] | None = None, files: int = 0) -> int:
    # The last `files` arguments are file names; print their count, not the list.
    shown = argv[: len(argv) - files] + ([f"<{files} files>"] if files else [])
    print("$ " + " ".join(shown), flush=True)
    # Fixed argument lists built in this file; no shell and no untrusted input.
    return subprocess.run(argv, cwd=ROOT, env=env, check=False).returncode  # noqa: S603


def tool(name: str) -> str | None:
    if name == "uv":
        return os.environ.get("UV") or shutil.which("uv")
    return shutil.which(name)


def check(
    name: str,
    argv: list[str] | None,
    missing: str = "",
    env: dict[str, str] | None = None,
) -> Result:
    print(f"\n=== {name} ===", flush=True)
    return execute(name, argv, missing, env)


def execute(
    name: str,
    argv: list[str] | None,
    missing: str = "",
    env: dict[str, str] | None = None,
    files: int = 0,
) -> Result:
    start = time.monotonic()
    if argv is None:
        print(f"FAIL: {missing}", flush=True)
        return Result(name, "fail", 0.0, missing)
    code = run(argv, env, files)
    status = "pass" if code == 0 else "fail"
    note = "" if code == 0 else f"exit {code}"
    return Result(name, status, time.monotonic() - start, note)


def commit_check() -> Result:
    name = "commit messages"
    print(f"\n=== {name} ===", flush=True)
    git = tool("git")
    if git is None:
        return execute(name, None, "git not found")
    base = subprocess.run(  # noqa: S603
        [git, "rev-parse", "--short", "origin/main"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # The range uses the local origin/main ref; the gate stays offline, never fetching.
    print(f"origin/main is {base.stdout.strip() or 'missing'} (fetch to refresh)")
    count = subprocess.run(  # noqa: S603
        [git, "rev-list", "--count", COMMIT_RANGE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if count.returncode != 0:
        note = f"cannot resolve {COMMIT_RANGE}; run `git fetch origin main`"
        print(f"FAIL: {note}\n{count.stderr.strip()}", flush=True)
        return Result(name, "fail", 0.0, note)
    if count.stdout.strip() == "0":
        note = f"no commits in {COMMIT_RANGE}"
        print(f"SKIP: {note}", flush=True)
        return Result(name, "skip", 0.0, note)
    return execute(
        name,
        [sys.executable, "-m", "commitizen", "check", "--rev-range", COMMIT_RANGE],
    )


def secrets_check() -> Result:
    name = "secrets"
    print(f"\n=== {name} ===", flush=True)
    git = tool("git")
    if git is None:
        return execute(name, None, "git not found")
    # Tracked files plus new unignored ones, so a secret is caught before commit.
    listed = subprocess.run(  # noqa: S603
        [git, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        return execute(name, None, "git ls-files failed")
    paths = {path for path in listed.stdout.decode("utf-8").split("\0") if path}
    files = sorted(path for path in paths if (ROOT / path).is_file())
    # The baseline carries the file exclusions; --no-verify keeps the scan offline.
    # Files go in batches so the command line stays under Windows' length limit. The
    # hook rewrites the baseline (and fails) only when it has entries whose lines moved
    # or after a detect-secrets upgrade; this baseline has no entries.
    hook = [
        sys.executable,
        "-m",
        "detect_secrets.pre_commit_hook",
        "--baseline",
        SECRETS_BASELINE,
        "--no-verify",
    ]
    start = time.monotonic()
    codes = [
        run([*hook, *batch], files=len(batch))
        for batch in (
            files[i : i + SECRETS_BATCH] for i in range(0, len(files), SECRETS_BATCH)
        )
    ]
    failed = [code for code in codes if code != 0]
    note = f"exit {failed[0]}" if failed else ""
    return Result(name, "fail" if failed else "pass", time.monotonic() - start, note)


def main() -> int:
    uv = tool("uv")
    node = tool("node")
    py = [sys.executable, "-m"]
    results = [
        check(
            "lockfile",
            [uv, "lock", "--check"] if uv else None,
            "uv not found",
        ),
        check("format", [*py, "ruff", "format", "--check"]),
        check("lint", [*py, "ruff", "check"]),
        check("types", [*py, "mypy"]),
        check("tests", [*py, "pytest", "--cov", "--cov-report=term-missing"]),
        check(
            "openspec",
            [
                node,
                str(OPENSPEC_CLI),
                "validate",
                "--all",
                "--strict",
                "--no-interactive",
            ]
            if node and OPENSPEC_CLI.is_file()
            else None,
            "node or the pinned OpenSpec CLI not found; run `npm ci --ignore-scripts`",
            # The OpenSpec CLI sends usage telemetry unless this is set.
            env={**os.environ, "OPENSPEC_TELEMETRY": "0"},
        ),
        secrets_check(),
        commit_check(),
    ]

    print("\n=== summary ===")
    for result in results:
        note = f"  ({result.note})" if result.note else ""
        print(
            f"{result.status.upper():4}  {result.name:16} {result.seconds:6.1f}s{note}"
        )
    failed = [result.name for result in results if result.status == "fail"]
    print("GATE FAILED: " + ", ".join(failed) if failed else "GATE PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
