"""The frozen scenario set scenarios-v1 (phase-5-calculator D5, D6)."""

import dataclasses

import pytest

from compute_cost_risk_monitor import scenarios
from compute_cost_risk_monitor.scenarios import PERCENT, SCENARIOS_V1, USD


def test_set_holds_the_four_approved_scenarios() -> None:
    assert scenarios.VERSION == "scenarios-v1"
    assert [(s.id, s.kind, s.magnitude) for s in SCENARIOS_V1] == [
        ("decline-25", PERCENT, -25.0),
        ("increase-25", PERCENT, 25.0),
        ("example-050", USD, 0.50),
        ("spike-100", PERCENT, 100.0),
    ]
    assert [s.name for s in SCENARIOS_V1] == [
        "Decline −25%",
        "Increase +25%",
        "PROJECT example +$0.50/GPU-hour",
        "Spike +100% (price doubles)",
    ]


def test_every_scenario_has_a_narrative_and_the_spike_names_its_motivation() -> None:
    assert all(s.narrative.strip() for s in SCENARIOS_V1)
    spike = SCENARIOS_V1[-1]
    assert "arXiv 2603.21690" in spike.narrative
    assert "not taken from any model" in spike.narrative
    hypothetical = [s for s in SCENARIOS_V1 if s.kind == PERCENT]
    assert all(s.narrative.startswith("Hypothetical") for s in hypothetical)


def test_labels_say_what_the_figures_are() -> None:
    assert scenarios.NOT_A_FORECAST == "Scenario calculation, not a forecast"
    assert "judgement" in scenarios.JUDGEMENT
    assert "not calibrated to history" in scenarios.JUDGEMENT


def test_set_cannot_be_changed_in_place() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        SCENARIOS_V1[0].magnitude = -50.0  # type: ignore[misc]
    assert isinstance(SCENARIOS_V1, tuple)
