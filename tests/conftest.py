"""Hypothesis profiles (Phase 6 design D11).

The `gate` profile is loaded everywhere, so local runs and CI (where Hypothesis would
otherwise switch to its own `ci` profile) generate the same examples. It keeps no
example database, so the tree stays clean. `HYPOTHESIS_PROFILE=explore` runs random,
longer searches by hand, outside the gate.
"""

import os

from hypothesis import settings

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
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "gate"))
