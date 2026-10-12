"""PROJECT.md §5 is the constitution; AGENTS.md and openspec/config.yaml copy its rules.

An amendment updates all three in one commit (PROJECT.md § Amending the constitution).
These checks fail when a copy drifts or the version line and amendment log disagree.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _section_5() -> str:
    text = (ROOT / "PROJECT.md").read_text(encoding="utf-8")
    match = re.search(r"^## 5\. .*?$(.*?)^## 6\. ", text, re.DOTALL | re.MULTILINE)
    assert match, "PROJECT.md has no §5 followed by §6"
    return match.group(1)


def _rules() -> list[str]:
    """The §5 bullets before its first subsection, each flattened to one line."""
    rules: list[str] = []
    for line in _section_5().splitlines():
        if line.startswith("#"):
            break
        if line.startswith("- "):
            rules.append(line[2:])
        elif line.startswith("  ") and rules:
            rules[-1] += " " + line
    return [_flat(rule) for rule in rules]


def test_constitution_lists_its_rules() -> None:
    assert len(_rules()) >= 5


@pytest.mark.parametrize("copy", ["AGENTS.md", "openspec/config.yaml"])
def test_copy_carries_every_rule_verbatim(copy: str) -> None:
    text = _flat((ROOT / copy).read_text(encoding="utf-8"))
    missing = [rule for rule in _rules() if rule not in text]
    assert not missing, f"{copy} lacks these PROJECT.md §5 rules verbatim: {missing}"


def test_version_line_matches_the_amendment_log() -> None:
    section = _section_5()
    line = re.search(
        r"\*\*Version (\d+\.\d+\.\d+)\*\* · Ratified (\S+) · Last amended (\S+)",
        section,
    )
    rows = re.findall(r"^\| (\d+\.\d+\.\d+) \| (\d{4}-\d{2}-\d{2}) \|", section, re.M)
    assert line, "§5 has no version line"
    assert rows, "§5 has no amendment log"
    version, ratified, amended = line.groups()
    assert (version, amended) == rows[-1]
    assert ratified == rows[0][1]
    order = [tuple(int(part) for part in v.split(".")) for v, _ in rows]
    assert order == sorted(set(order)), "amendment log versions must strictly increase"
