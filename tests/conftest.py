"""Hypothesis profiles (Phase 6 design D11).

The `gate` profile is loaded everywhere, so local runs and CI (where Hypothesis would
otherwise switch to its own `ci` profile) generate the same examples. It keeps no
example database, so the tree stays clean. `HYPOTHESIS_PROFILE=explore` runs random,
longer searches by hand, outside the gate.
"""

import os

import pytest
from hypothesis import settings

PROFILES = ("gate", "explore")

settings.register_profile(
    "gate",
    derandomize=True,
    database=None,
    deadline=None,
    max_examples=200,
    print_blob=True,
)
settings.register_profile(
    "explore", derandomize=False, database=None, deadline=None, max_examples=2000
)
# An empty variable means the default; a name this file does not register stops the run
# with one clear message instead of a Hypothesis error in every test module.
_chosen = os.environ.get("HYPOTHESIS_PROFILE") or "gate"
if _chosen not in PROFILES:
    raise pytest.UsageError(
        f"HYPOTHESIS_PROFILE={_chosen!r} is not a profile here; use one of {PROFILES}"
    )
settings.load_profile(_chosen)
