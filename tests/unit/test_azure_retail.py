"""Azure Retail Prices rules, checked against known answers on synthetic items."""

import copy
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from compute_cost_risk_monitor import azure_retail as az

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"
ITEMS = json.loads((FIXTURES / "azure_items.json").read_text(encoding="utf-8"))
DOCS_NEXT_LINK = (
    "https://prices.azure.com:443/api/retail/prices"
    "?$filter=serviceName%20eq%20%27Virtual%20Machines%27&$skip=1000"
)
# A fake credential: next links that carry one must be refused.
CRED = "https://user:pw@prices.azure.com/api/retail/prices"  # pragma: allowlist secret


def build(case: dict[str, Any]) -> object:
    if "replace" in case:
        return case["replace"]
    item = copy.deepcopy(ITEMS["base"])
    item.update(case.get("set", {}))
    for field in case.get("drop", []):
        del item[field]
    return item


def test_fixture_is_labelled_synthetic() -> None:
    assert ITEMS["_label"] == "synthetic"
    assert {case["kind"] for case in ITEMS["cases"]} == {"normal", "edge", "failing"}


@pytest.mark.parametrize("case", ITEMS["cases"], ids=lambda case: case["name"])
def test_item_known_answers(case: dict[str, Any]) -> None:
    expect = case["expect"]
    verdict = az.classify(build(case))
    assert verdict.outcome == expect["outcome"]
    assert verdict.reason == expect.get("reason")
    if expect["outcome"] != "stored":
        assert verdict.row is None
        return
    row = verdict.row
    assert row is not None
    assert row.rental_type == expect["rental_type"]
    assert row.price_unit == expect["price_unit"]
    assert list(row.flags) == expect["flags"]
    if "item_key" in expect:
        assert row.item_key == expect["item_key"]
    if "savings_plan" in expect:
        assert row.savings_plan == expect["savings_plan"]


def test_stored_row_keeps_azure_values_verbatim() -> None:
    case = next(c for c in ITEMS["cases"] if c["name"] == "reservation names its term")
    row = az.classify(build(case)).row
    assert row is not None
    assert (row.retail_price, row.unit_of_measure, row.reservation_term) == (
        25007.0,
        "1 Hour",
        "1 Year",
    )
    assert row.effective_start_date == datetime(2026, 1, 1, tzinfo=UTC)
    assert row.is_primary_meter_region is True


def test_optional_fields_stay_missing() -> None:
    case = next(c for c in ITEMS["cases"] if c["name"] == "optional fields absent")
    row = az.classify(build(case)).row
    assert row is not None
    assert (row.unit_price, row.effective_start_date, row.location) == (
        None,
        None,
        None,
    )
    assert row.savings_plan is None and row.reservation_term is None


@pytest.mark.parametrize("price", [math.nan, math.inf, -math.inf])
def test_non_finite_price_rejected(price: float) -> None:
    item = copy.deepcopy(ITEMS["base"])
    item["retailPrice"] = price
    assert az.classify(item) == az.Verdict("rejected", "non_finite_price")


def test_sizes_sharing_a_meter_share_the_meter_key() -> None:
    first = az.classify(copy.deepcopy(ITEMS["base"])).row
    other = copy.deepcopy(ITEMS["base"])
    other["armSkuName"] = "Standard_NC40ads_H100_v5_Promo"
    second = az.classify(other).row
    assert first is not None and second is not None
    assert first.item_key != second.item_key
    assert first.meter_key == second.meter_key


def test_item_key_writes_whole_tiers_as_decimals() -> None:
    key = az.item_key("m", "s", "eastus", "Consumption", None, 0, "USD", "Standard_NC6")
    assert key == "m|s|eastus|Consumption||0.0|USD|Standard_NC6"


def test_first_page_url_is_the_fixed_request() -> None:
    assert az.first_page_url() == (
        "https://prices.azure.com/api/retail/prices"
        "?api-version=2023-01-01-preview"
        "&currencyCode=%27USD%27"
        "&meterRegion=%27primary%27"
        "&$filter=serviceName%20eq%20%27Virtual%20Machines%27%20and%20"
        "contains%28armSkuName%2C%20%27Standard_N%27%29"
    )
    assert az.next_link_problem(az.first_page_url()) is None
    assert az.missing_params(az.first_page_url()) == []


@pytest.mark.parametrize(
    ("link", "problem"),
    [
        (DOCS_NEXT_LINK, None),
        (DOCS_NEXT_LINK.replace("https:", "http:"), "scheme"),
        ("https://prices.azure.com.evil.test/api/retail/prices?$skip=1", "host"),
        ("https://prices.azure.com@evil.test/api/retail/prices?$skip=1", "host"),
        ("https://prices.azure.com:8443/api/retail/prices?$skip=1", "port"),
        ("https://prices.azure.com/api/retail/other?$skip=1", "path"),
        (CRED, "credentials"),
        ("https://prices.azure.com:notaport/api/retail/prices", "unparseable"),
    ],
)
def test_next_link_must_point_at_the_api(link: str, problem: str | None) -> None:
    assert az.next_link_problem(link) == problem


def test_next_link_that_drops_fixed_parameters_is_noticed() -> None:
    assert az.missing_params(az.first_page_url() + "&$skip=1000") == []
    assert az.missing_params(DOCS_NEXT_LINK) == [
        "api-version",
        "currencyCode",
        "meterRegion",
        "$filter",
    ]


@pytest.mark.parametrize(
    ("price_type", "meter", "sku", "expected"),
    [
        ("Reservation", "X Spot", "X", ("reservation", None)),
        ("DevTestConsumption", "X Spot", "X Spot", ("dev_test", None)),
        ("Consumption", "X Spot", "X Spot", ("spot", None)),
        ("Consumption", "X Low Priority", "X Low Priority", ("other", None)),
        ("Consumption", "X", "X", ("on_demand", None)),
        ("Consumption", "X", "X Low Priority", ("other", "rental_type_ambiguous")),
        ("Consumption", "Spotless X", "Spotless X", ("on_demand", None)),
        ("Bid", "X", "X", ("other", "unknown_price_type")),
    ],
)
def test_rental_type_rules(
    price_type: str, meter: str, sku: str, expected: tuple[str, str | None]
) -> None:
    assert az.rental_type(price_type, meter, sku) == expected


@pytest.mark.parametrize("field", ["retailPrice", "tierMinimumUnits", "unitPrice"])
def test_integers_too_large_for_a_float_are_rejected(field: str) -> None:
    item = copy.deepcopy(ITEMS["base"])
    item[field] = 10**400
    assert az.classify(item) == az.Verdict("rejected", "invalid_value")


@pytest.mark.parametrize(
    "link",
    [
        DOCS_NEXT_LINK + "\n",
        DOCS_NEXT_LINK.replace("&", "\n&"),
        DOCS_NEXT_LINK.replace("$skip", " $skip"),
        DOCS_NEXT_LINK + "\t",
        DOCS_NEXT_LINK + "é",
    ],
)
def test_next_link_with_stray_characters_is_refused(link: str) -> None:
    assert az.next_link_problem(link) == "characters"
