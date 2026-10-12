"""Azure Retail Prices rules: the fixed request, next-page checks and item handling.

Pure functions only, with no network, files or database. The fetch loop and the ingest
step both call these, so each rule has one home and known-answer tests
(phase-2-collector design D3-D7, D17, D26).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import parse_qs, quote, urlsplit

SOURCE = "azure-retail"
ENDPOINT = "https://prices.azure.com/api/retail/prices"
HOST = "prices.azure.com"
PATH = "/api/retail/prices"
PAGE_SIZE = 1000
GPU_FAMILIES = ("Standard_NC", "Standard_ND", "Standard_NG", "Standard_NV")

# The one request this collector makes. Filter values are case-sensitive in this
# version, which is also the only one that returns savings-plan prices.
PARAMS: tuple[tuple[str, str], ...] = (
    ("api-version", "2023-01-01-preview"),
    ("currencyCode", "'USD'"),
    ("meterRegion", "'primary'"),
    (
        "$filter",
        "serviceName eq 'Virtual Machines' and contains(armSkuName, 'Standard_N')",
    ),
)

_REQUIRED_TEXT = (
    "meterId",
    "skuId",
    "armRegionName",
    "type",
    "unitOfMeasure",
    "currencyCode",
    "meterName",
    "skuName",
)
_OPTIONAL_TEXT = (
    "location",
    "productId",
    "productName",
    "serviceName",
    "serviceFamily",
    "reservationTerm",
)


def first_page_url() -> str:
    """The fixed first request, every value percent-encoded."""
    query = "&".join(f"{key}={quote(value, safe='')}" for key, value in PARAMS)
    return f"{ENDPOINT}?{query}"


def next_link_problem(link: str) -> str | None:
    """Why a NextPageLink must not be followed, or None when it points at the API."""
    try:
        parts = urlsplit(link)
        port = parts.port
    except ValueError:
        return "unparseable"
    if parts.scheme != "https":
        return "scheme"
    if parts.hostname != HOST:
        return "host"
    if port not in (None, 443):
        return "port"
    if parts.path != PATH:
        return "path"
    if parts.username is not None or parts.password is not None:
        return "credentials"
    return None


def missing_params(link: str) -> list[str]:
    """Fixed parameters that a next link drops or changes."""
    query = parse_qs(urlsplit(link).query, keep_blank_values=True)
    return [key for key, value in PARAMS if query.get(key) != [value]]


@dataclass(frozen=True)
class Page:
    items: list[object]
    next_link: object  # validated by the caller: None, empty or a link to check


def parse_page(body: bytes) -> Page | None:
    """A page's items and next link, or None when the body is not a valid page."""
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(document, dict) or not isinstance(document.get("Items"), list):
        return None
    return Page(document["Items"], document.get("NextPageLink"))


@dataclass(frozen=True)
class Row:
    """An in-scope, valid item, shaped for price_observation and azure_retail_price."""

    item_key: str
    meter_key: str  # the item key without armSkuName, for the shared_meter_key flag
    rental_type: str
    price_unit: str
    flags: tuple[str, ...]
    meter_id: str
    sku_id: str
    arm_sku_name: str
    arm_region_name: str
    location: str | None
    price_type: str
    retail_price: float
    unit_price: float | None
    unit_of_measure: str
    effective_start_date: datetime | None
    product_id: str | None
    product_name: str | None
    sku_name: str
    meter_name: str
    service_name: str | None
    service_family: str | None
    is_primary_meter_region: bool
    reservation_term: str | None
    tier_minimum_units: float
    savings_plan: str | None  # the savingsPlan array as JSON text


@dataclass(frozen=True)
class Verdict:
    outcome: Literal["stored", "out_of_scope", "rejected"]
    reason: str | None = None
    row: Row | None = None


def _rejected(reason: str) -> Verdict:
    return Verdict("rejected", reason)


def _is_number(value: object) -> bool:
    # bool is an int in Python, but never a price.
    return isinstance(value, int | float) and not isinstance(value, bool)


def rental_type(
    price_type: str, meter_name: str, sku_name: str
) -> tuple[str, str | None]:
    """Rental type and any flag, by the first rule that matches (design D5)."""
    if price_type == "Reservation":
        return "reservation", None
    if price_type == "DevTestConsumption":
        return "dev_test", None
    if price_type != "Consumption":
        return "other", "unknown_price_type"
    meter = (meter_name.endswith(" Spot"), meter_name.endswith(" Low Priority"))
    sku = (sku_name.endswith(" Spot"), sku_name.endswith(" Low Priority"))
    if meter != sku:
        return "other", "rental_type_ambiguous"
    spot, low_priority = meter
    if spot:
        return "spot", None
    if low_priority:
        return "other", None
    return "on_demand", None


def item_key(
    meter_id: str,
    sku_id: str,
    region: str,
    price_type: str,
    reservation_term: str | None,
    tier_minimum_units: float,
    currency: str,
    arm_sku_name: str,
) -> str:
    """Phase 1 D15's duplicate key plus armSkuName (design D6)."""
    parts = [
        meter_id,
        sku_id,
        region,
        price_type,
        reservation_term or "",
        repr(float(tier_minimum_units)),
        currency,
        arm_sku_name,
    ]
    return "|".join(parts)


def price_unit(price_type: str, unit_of_measure: str, term: str | None) -> str:
    """A reservation is priced for its whole term, so its unit names the term."""
    if price_type == "Reservation" and term:
        return f"{term} term"
    return unit_of_measure


def _start_date(value: object) -> datetime | None | Literal[False]:
    """Parsed effectiveStartDate, None when absent, False when invalid."""
    if value is None:
        return None
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed if parsed.tzinfo is not None else False


def classify(item: object) -> Verdict:
    """Sort an API item into stored, out of scope or rejected; never fill a value in."""
    if not isinstance(item, dict):
        return _rejected("not_an_object")
    sku = item.get("armSkuName")
    if sku is None:
        return _rejected("missing_field")
    if not isinstance(sku, str) or not sku:
        return _rejected("invalid_value")
    if not sku.startswith(GPU_FAMILIES):
        return Verdict("out_of_scope")

    for field in (*_REQUIRED_TEXT, "retailPrice", "isPrimaryMeterRegion"):
        if item.get(field) is None:
            return _rejected("missing_field")
    if "tierMinimumUnits" not in item or item["tierMinimumUnits"] is None:
        return _rejected("missing_field")
    if any(not isinstance(item[f], str) or not item[f] for f in _REQUIRED_TEXT):
        return _rejected("invalid_value")
    price, tier = item["retailPrice"], item["tierMinimumUnits"]
    primary = item["isPrimaryMeterRegion"]
    if not _is_number(price) or not _is_number(tier) or not isinstance(primary, bool):
        return _rejected("invalid_value")

    if item["currencyCode"] != "USD":
        return _rejected("non_usd_currency")
    if not primary:
        return _rejected("not_primary_meter")
    if not math.isfinite(price):
        return _rejected("non_finite_price")
    if price <= 0:
        return _rejected("non_positive_price")
    if not math.isfinite(tier) or tier < 0:
        return _rejected("invalid_value")

    for field in _OPTIONAL_TEXT:
        value = item.get(field)
        if value is not None and (not isinstance(value, str) or not value):
            return _rejected("invalid_value")
    unit = item.get("unitPrice")
    if unit is not None and (
        not _is_number(unit) or not math.isfinite(unit) or unit < 0
    ):
        return _rejected("invalid_value")
    start = _start_date(item.get("effectiveStartDate"))
    if start is False:
        return _rejected("invalid_value")
    plan = item.get("savingsPlan")
    if plan is not None and not isinstance(plan, list):
        return _rejected("invalid_value")
    term = item.get("reservationTerm")
    if item["type"] == "Reservation" and term is None:
        return _rejected("reservation_without_term")

    kind, flag = rental_type(item["type"], item["meterName"], item["skuName"])
    flags = [flag] if flag else []
    if item["type"] != "Reservation" and item["unitOfMeasure"] != "1 Hour":
        flags.append("unit_not_hourly")
    key = item_key(
        item["meterId"],
        item["skuId"],
        item["armRegionName"],
        item["type"],
        term,
        tier,
        item["currencyCode"],
        sku,
    )
    row = Row(
        item_key=key,
        meter_key=key.rsplit("|", 1)[0],
        rental_type=kind,
        price_unit=price_unit(item["type"], item["unitOfMeasure"], term),
        flags=tuple(flags),
        meter_id=item["meterId"],
        sku_id=item["skuId"],
        arm_sku_name=sku,
        arm_region_name=item["armRegionName"],
        location=item.get("location"),
        price_type=item["type"],
        retail_price=float(price),
        unit_price=None if unit is None else float(unit),
        unit_of_measure=item["unitOfMeasure"],
        effective_start_date=start,
        product_id=item.get("productId"),
        product_name=item.get("productName"),
        sku_name=item["skuName"],
        meter_name=item["meterName"],
        service_name=item.get("serviceName"),
        service_family=item.get("serviceFamily"),
        is_primary_meter_region=primary,
        reservation_term=term,
        tier_minimum_units=float(tier),
        savings_plan=None if plan is None else json.dumps(plan, separators=(",", ":")),
    )
    return Verdict("stored", row=row)
