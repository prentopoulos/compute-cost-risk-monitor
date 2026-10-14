"""The committed Streamlit settings keep the dashboard local (Phase 4 D11, D12, D31).

The file sits beside the app script, where Streamlit reads it whatever folder the
dashboard is launched from.
"""

import tomllib
from pathlib import Path

import pytest
from streamlit import config as streamlit_config

from compute_cost_risk_monitor import dashboard

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "src" / "compute_cost_risk_monitor" / "app.py"
CONFIG = APP.parent / ".streamlit" / "config.toml"


def _config() -> dict[str, dict[str, object]]:
    with CONFIG.open("rb") as handle:
        return tomllib.load(handle)


def test_usage_statistics_are_off() -> None:
    assert _config()["browser"]["gatherUsageStats"] is False


def test_server_listens_on_this_pc_only() -> None:
    assert _config()["server"]["address"] == "127.0.0.1"


def test_streamlit_menu_is_hidden() -> None:
    # No developer options, Deploy button or theme switch (Phase 7 design D47).
    assert _config()["client"]["toolbarMode"] == "minimal"


def test_streamlit_reads_it_from_any_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # `streamlit run` records the script path here before reading config files.
    monkeypatch.setattr(streamlit_config, "_main_script_path", str(APP))
    files = [
        Path(f).resolve() for f in streamlit_config.get_config_files("config.toml")
    ]
    assert CONFIG.resolve() in files


def test_no_config_at_the_repo_root() -> None:
    # One file only: a copy at the root could drift or add settings when launched there.
    assert not (ROOT / ".streamlit" / "config.toml").exists()


def test_streamlit_secrets_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "**/.streamlit/secrets.toml" in ignored


# --- the desk theme (Phase 7 design D4, D10, D13, D16, D24, D26) ---


def _theme() -> dict[str, object]:
    theme = _config()["theme"]
    assert isinstance(theme, dict)
    return theme


def _luminance(colour: str) -> float:
    """WCAG 2.2 relative luminance of a #RRGGBB colour."""
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_contrast_matches_the_wcag_formula() -> None:
    assert contrast("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)


def test_one_dark_theme_with_bundled_fonts() -> None:
    theme = _theme()
    assert theme["base"] == "dark"
    assert "light" not in theme and "dark" not in theme
    assert "fontFaces" not in theme and "font" not in theme
    assert "enableStaticServing" not in _config()["server"]


def test_dashboard_colours_match_the_theme() -> None:
    theme = _theme()
    pairs = {
        "background": "backgroundColor",
        "panel": "secondaryBackgroundColor",
        "text": "textColor",
        "accent": "primaryColor",
        "border": "borderColor",
        "red": "redColor",
        "green": "greenColor",
        "amber": "orangeColor",
    }
    for name, key in pairs.items():
        assert dashboard.COLOURS[name] == theme[key], key
    # Tags are inline code: muted on the panel colour, never the saving green.
    assert theme["codeTextColor"] == dashboard.COLOURS["muted"]
    assert theme["codeBackgroundColor"] == dashboard.COLOURS["panel"]
    for colour in ("red", "green", "orange", "yellow", "blue", "gray"):
        assert theme[f"{colour}TextColor"] == theme[f"{colour}Color"]
    assert dashboard.POINT_COLOUR in dashboard.COLOURS.values()
    assert set(dashboard.RULE_COLOURS) <= set(dashboard.COLOURS.values())


@pytest.mark.parametrize("colour", ["text", "red", "green", "accent", "amber", "muted"])
@pytest.mark.parametrize("ground", ["background", "panel", "shade"])
def test_text_colours_reach_4_5_to_1(colour: str, ground: str) -> None:
    ratio = contrast(dashboard.COLOURS[colour], dashboard.COLOURS[ground])
    assert ratio >= 4.5, f"{colour} on {ground}: {ratio:.2f}"


@pytest.mark.parametrize("ground", ["background", "panel"])
def test_control_borders_reach_3_to_1(ground: str) -> None:
    ratio = contrast(dashboard.COLOURS["border"], dashboard.COLOURS[ground])
    assert ratio >= 3.0, f"border on {ground}: {ratio:.2f}"


def test_no_injected_css() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "<style" not in source, path
        assert "unsafe_allow_html" not in source, path
        assert "st.html(" not in source, path
