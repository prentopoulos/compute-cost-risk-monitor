"""The committed Streamlit settings keep the dashboard local (Phase 4 D11, D12, D31).

The file sits beside the app script, where Streamlit reads it whatever folder the
dashboard is launched from.
"""

import tomllib
from pathlib import Path

import pytest
from streamlit import config as streamlit_config

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


def test_developer_options_are_hidden() -> None:
    assert _config()["client"]["toolbarMode"] == "viewer"


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
