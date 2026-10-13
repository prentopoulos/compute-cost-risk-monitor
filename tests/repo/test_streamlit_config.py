"""The committed Streamlit settings keep the dashboard local (Phase 4 design D11, D12).

Streamlit reads `.streamlit/config.toml` from the folder it is launched in, so the
dashboard is launched from the repository root.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _config() -> dict[str, dict[str, object]]:
    with (ROOT / ".streamlit" / "config.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_usage_statistics_are_off() -> None:
    assert _config()["browser"]["gatherUsageStats"] is False


def test_server_listens_on_this_pc_only() -> None:
    assert _config()["server"]["address"] == "127.0.0.1"


def test_developer_options_are_hidden() -> None:
    assert _config()["client"]["toolbarMode"] == "viewer"


def test_streamlit_secrets_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".streamlit/secrets.toml" in ignored
