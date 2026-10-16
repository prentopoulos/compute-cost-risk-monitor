"""The README against the committed brief, its licence and links (public-release spec).

The README opens with the bottom line of the committed synthetic brief, between two
HTML comment markers. Every number there must equal a bottom-line fact in
docs/brief/facts.json as displayed, once the snapshot time and the GPU, size and
region names are set aside.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
FACTS = ROOT / "docs" / "brief" / "facts.json"
START, END = "<!-- bottom-line:start -->", "<!-- bottom-line:end -->"
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
LINK = re.compile(r"\]\(([^)\s]+)\)")
LABEL = "SYNTHETIC DATA — NOT AZURE LIST PRICES"


def facts() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FACTS.read_text(encoding="utf-8"))
    return loaded


def bottom_line(text: str) -> str:
    return text[text.index(START) + len(START) : text.index(END)]


def unmatched(section: str, fact_set: dict[str, Any]) -> list[str]:
    """Numbers in the section that equal no bottom-line fact as displayed."""
    bottom = {
        key: fact for key, fact in fact_set["facts"].items() if key.startswith("bl_")
    }
    shown = {fact["text"] for fact in bottom.values()}
    names = {fact["text"] for fact in bottom.values() if fact["unit"] == "text"}
    masked = section.replace(fact_set["as_of"], " ")
    for name in sorted(names | set(fact_set["names"]), key=len, reverse=True):
        masked = masked.replace(name, " ")
    return [number for number in NUMBER.findall(masked) if number not in shown]


def test_readme_opens_with_the_brief_bottom_line() -> None:
    text = README.read_text(encoding="utf-8")
    fact_set = facts()
    section = bottom_line(text)
    assert text.index(START) < text.index("## ")
    assert LABEL in section
    assert fact_set["as_of"] in section
    assert fact_set["facts"]["bl_cost"]["text"] in section
    assert "not a forecast" in section
    assert unmatched(section, fact_set) == []


def test_a_drifted_figure_is_named() -> None:
    section = bottom_line(README.read_text(encoding="utf-8"))
    drifted = section.replace("69,120.00", "69,120.01")
    assert unmatched(drifted, facts()) == ["69,120.01"]


def test_licence_and_credits() -> None:
    text = README.read_text(encoding="utf-8")
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    assert "[MIT License](LICENSE)" in text
    assert "CC BY 4.0" in text
    assert "src/compute_cost_risk_monitor/reference/README.md" in text
    assert ".agents/skills/grilling/LICENSE" in text


def test_every_local_readme_link_is_a_tracked_file() -> None:
    git = shutil.which("git")
    assert git is not None
    tracked = set(
        subprocess.run(  # noqa: S603 (fixed arguments, no shell)
            [git, "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    )
    links = [
        target.split("#", 1)[0]
        for target in LINK.findall(README.read_text(encoding="utf-8"))
        if not target.startswith(("http://", "https://", "#"))
    ]
    assert links
    assert [link for link in links if link not in tracked] == []
