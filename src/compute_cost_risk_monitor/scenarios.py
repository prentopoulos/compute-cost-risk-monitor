"""Frozen hypothetical price changes: scenarios-v1 (phase-5 D5, D6) and the scenario
ladder ladder-v1 (phase-7 D7).

Data only, so the calculator and its independent check (`workload_check`) read the same
definitions without either importing the other. The magnitudes are round sensitivities
chosen by judgement: one snapshot holds no history to calibrate them, and no model's
numbers are used. A changed scenario or step needs a new set version, never an edit in
place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

VERSION: Final = "scenarios-v1"
PERCENT: Final = "percent"  # magnitude in percent of the starting price
USD: Final = "usd"  # magnitude in USD per GPU-hour
Kind = Literal["percent", "usd"]

NOT_A_FORECAST: Final = "Scenario calculation, not a forecast"
JUDGEMENT: Final = (
    "Round sensitivities chosen by judgement, not calibrated to history (one snapshot)"
    " or to any model."
)


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    kind: Kind
    magnitude: float
    narrative: str


SCENARIOS_V1: Final[tuple[Scenario, ...]] = (
    Scenario(
        "decline-25",
        "Decline −25%",
        PERCENT,
        -25.0,
        "Hypothetical list-price cut: the price of this size falls by a quarter.",
    ),
    Scenario(
        "increase-25",
        "Increase +25%",
        PERCENT,
        25.0,
        "Hypothetical list-price rise: the price of this size rises by a quarter.",
    ),
    Scenario(
        "example-050",
        "PROJECT example +$0.50/GPU-hour",
        USD,
        0.50,
        "PROJECT.md's worked example: a flat rise of USD 0.50 per GPU-hour, whatever"
        " the starting price.",
    ),
    Scenario(
        "spike-100",
        "Spike +100% (price doubles)",
        PERCENT,
        100.0,
        "Hypothetical demand shock: the price doubles. Jump models of compute costs"
        " (e.g. arXiv 2603.21690) motivate testing a jump; its size is not taken from"
        " any model.",
    ),
)

LADDER_VERSION: Final = "ladder-v1"


@dataclass(frozen=True)
class Step:
    """One ladder row: a change of the starting price, labelled by the change itself."""

    id: str
    label: str
    kind: Kind
    magnitude: float


LADDER_V1: Final[tuple[Step, ...]] = (
    Step("down-50", "−50%", PERCENT, -50.0),
    Step("down-25", "−25%", PERCENT, -25.0),
    Step("down-10", "−10%", PERCENT, -10.0),
    Step("up-10", "+10%", PERCENT, 10.0),
    Step("up-25", "+25%", PERCENT, 25.0),
    Step("up-50", "+50%", PERCENT, 50.0),
    Step("up-100", "+100%", PERCENT, 100.0),
    Step("flat-050", "+0.50 USD/GPU-h", USD, 0.50),  # PROJECT.md's worked example
)
# The ladder's GPU columns; whole VMs at 1, 2, 4 and 8 GPUs per VM.
LADDER_GPUS: Final[tuple[int, ...]] = (8, 16, 32, 64, 128)
