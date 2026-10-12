"""Rule set groups-v1: every parameter normalization and the group rules read, frozen.

The constant below is stored once in `rule_set` and never changed in place. A different
rule needs a new version (phase-3-normalization design D2, D4-D8, D15, D19-D21).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import duckdb

RULE_VERSION = "groups-v1"
DESCRIPTION = (
    "Linux pay-as-you-go and Spot list prices in commercial regions, for mapped "
    "whole-GPU sizes not retired, normalized to USD per GPU-hour "
    "(phase-3-normalization)"
)

_LEARN = "https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/lifecycle/retirement/"

GROUPS_V1: dict[str, Any] = {
    "rule_version": RULE_VERSION,
    "map_version": "gpu-map-v1",
    "compared_rental_types": ["on_demand", "spot"],
    "exclusion_order": [
        "rental_type_not_compared",
        "government_cloud",
        "windows",
        "unit_not_hourly",
        "unmapped_sku",
        "fractional_gpu",
        "retired_size",
    ],
    "marketplace_exclusion_order": ["rental_type_not_compared", "unmapped_gpu_name"],
    # Synthetic marketplace GPU names onto variant labels (design D8). The
    # marketplace is fictional; these names only exercise the marketplace rules.
    "marketplace_gpu_names": {
        "H100 SXM": {"variant": "H100 NVLink 80GB", "vram_gb": 80},
        "H100 PCIe": {"variant": "H100 PCIe 80GB", "vram_gb": 80},
        "A100 SXM": {"variant": "A100 NVLink 80GB", "vram_gb": 80},
        "L40S": {"variant": "L40S 48GB", "vram_gb": 48},
        "RTX 4090": {"variant": "RTX 4090 24GB", "vram_gb": 24},
    },
    "government_region_prefixes": ["usgov", "usdod"],
    "windows_product_suffixes": ["Windows", "Win"],
    "hourly_unit": "1 Hour",
    # Learn's retirement date per series. A region Learn names in an extension keeps the
    # size until that region's date.
    "retirements": [
        {
            "series": "NC-series, including NC_Promo",
            "sizes": [
                "Standard_NC6",
                "Standard_NC12",
                "Standard_NC24",
                "Standard_NC24r",
                "Standard_NC6_Promo",
                "Standard_NC12_Promo",
                "Standard_NC24_Promo",
                "Standard_NC24r_Promo",
            ],
            "retired_on": "2023-09-06",
            "region_extensions": {},
            "source_url": "https://learn.microsoft.com/en-us/previous-versions/azure/"
            "virtual-machines/sizes/retirement/nc-series-retirement",
        },
        {
            "series": "NV-series, including NV_Promo",
            "sizes": [
                "Standard_NV6",
                "Standard_NV12",
                "Standard_NV24",
                "Standard_NV6_Promo",
                "Standard_NV12_Promo",
                "Standard_NV24_Promo",
            ],
            "retired_on": "2023-09-06",
            "region_extensions": {},
            "source_url": _LEARN + "nv-series-retirement",
        },
        {
            "series": "NCv3-series, including NC24rs_v3",
            "sizes": [
                "Standard_NC6s_v3",
                "Standard_NC12s_v3",
                "Standard_NC24s_v3",
                "Standard_NC24rs_v3",
            ],
            "retired_on": "2025-09-30",
            "region_extensions": {
                "usgovarizona": "2026-12-31",
                "usgovvirginia": "2026-12-31",
                "jioindiawest": "2027-06-30",
            },
            "source_url": _LEARN + "ncv3-retirement",
        },
        {
            "series": "NVv3-series",
            "sizes": ["Standard_NV12s_v3", "Standard_NV24s_v3", "Standard_NV48s_v3"],
            "retired_on": "2026-09-30",
            "region_extensions": {"uaenorth": "2027-01-31"},
            "source_url": _LEARN + "nvv3-series-retirement",
        },
        {
            "series": "NVv4-series",
            "sizes": [
                "Standard_NV4as_v4",
                "Standard_NV8as_v4",
                "Standard_NV16as_v4",
                "Standard_NV32as_v4",
            ],
            "retired_on": "2026-09-30",
            "region_extensions": {},
            "source_url": _LEARN + "nvv4-retirement",
        },
    ],
    "stale_after_days": 7,
    "thin_below_regions": 5,
    "thin_below_machines": 5,
    "not_listed_after_absences": 2,
    "exclusions": (
        "Excludes disks and storage, egress, public IPs, licences, taxes, "
        "negotiated discounts, reservations and savings plans, Spot eviction risk, "
        "capacity and quota."
    ),
}


class FrozenMismatch(Exception):
    """A stored rule set or map row differs from the code's version of it."""


def store(
    connection: duckdb.DuckDBPyConnection,
    created_at: datetime,
    parameters: dict[str, Any] | None = None,
) -> bool:
    """Store the rule set if absent; True when written. Refuse a changed one."""
    params = GROUPS_V1 if parameters is None else parameters
    version = params["rule_version"]
    row = connection.execute(
        "SELECT parameters FROM rule_set WHERE rule_version = ?", [version]
    ).fetchone()
    if row is not None:
        if json.loads(row[0]) != params:
            raise FrozenMismatch(f"stored rule set {version} differs from the code")
        return False
    connection.execute(
        "INSERT INTO rule_set VALUES (?, ?, ?, ?)",
        [version, created_at, DESCRIPTION, json.dumps(params, sort_keys=True)],
    )
    return True


def stored(connection: duckdb.DuckDBPyConnection, version: str) -> dict[str, Any]:
    """The parameters stored for a rule version; KeyError when it is not stored."""
    row = connection.execute(
        "SELECT parameters FROM rule_set WHERE rule_version = ?", [version]
    ).fetchone()
    if row is None:
        raise KeyError(version)
    value: dict[str, Any] = json.loads(row[0])
    return value
