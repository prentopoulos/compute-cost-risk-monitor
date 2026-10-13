"""Seed in-memory databases with synthetic Azure runs for normalization and group tests.

Everything here is synthetic: sizes are real Azure names so the packaged map applies,
but prices, regions and products are invented round numbers with known answers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb

from compute_cost_risk_monitor import db

DAY = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Price:
    """One synthetic Azure observation."""

    size: str = "Standard_ND96isr_H100_v5"
    region: str = "westeurope"
    rental: str = "on_demand"
    price: float = 80.0
    product: str | None = "Virtual Machines NDsr H100 v5 Series"
    unit: str = "1 Hour"
    meter: str = ""  # distinguishes otherwise equal item keys

    def key(self) -> str:
        return "|".join(
            [self.meter or "m", self.size, self.region, self.rental, self.unit]
        )


def database() -> duckdb.DuckDBPyConnection:
    connection = db.connect()
    db.create_schema(connection)
    return connection


def azure_run(
    connection: duckdb.DuckDBPyConnection,
    run_id: str,
    prices: list[Price],
    started: datetime = DAY,
    status: str = "succeeded",
    tallies: dict[tuple[str, str], int] | None = None,
    repeats: int = 0,
) -> None:
    """One synthetic Azure run with one raw response holding every price."""
    received = started + timedelta(seconds=2)
    connection.execute(
        "INSERT INTO collection_run VALUES (?, 'azure-retail', 'synthetic', ?, ?, ?,"
        " 'test', 1, NULL, NULL, NULL)",
        [run_id, started, received, status],
    )
    response = f"{run_id}-0000"
    connection.execute(
        "INSERT INTO raw_response VALUES (?, ?, 'azure-retail', 0, 'synthetic.json.gz',"
        " ?, 10, 'https://prices.azure.com/api/retail/prices', 200, ?, ?, ?,"
        " 'parsed', NULL)",
        [response, run_id, "0" * 64, started, received, len(prices)],
    )
    for price in prices:
        connection.execute(
            "INSERT INTO price_observation VALUES ('azure-retail', ?, ?, ?, ?, ?, ?,"
            " 'USD', ?, NULL, NULL)",
            [
                price.key(),
                received,
                response,
                price.rental,
                price.region,
                price.price,
                price.unit,
            ],
        )
        connection.execute(
            "INSERT INTO azure_retail_price (source, item_key, retrieved_at, meter_id,"
            " sku_id, arm_sku_name, arm_region_name, location, price_type,"
            " retail_price, unit_price, unit_of_measure, product_name,"
            " is_primary_meter_region,"
            " tier_minimum_units) VALUES ('azure-retail', ?, ?, ?, 'SYNTH/0001', ?, ?,"
            " 'Synthetic', 'Consumption', ?, ?, '1 Hour', ?, true, 0)",
            [
                price.key(),
                received,
                price.meter or "m",
                price.size,
                price.region,
                price.price,
                price.price,
                price.product,
            ],
        )
    rejected = sum(
        count for (kind, _), count in (tallies or {}).items() if kind == "rejected"
    )
    connection.execute(
        "INSERT INTO collection_run_summary"
        " VALUES (?, 'azure-retail', 1, 1, 0, 0, ?, ?, ?, 0, ?, ?)",
        [
            run_id,
            len(prices) + repeats + rejected,
            len(prices),
            repeats,
            rejected,
            "completed" if status == "succeeded" else "page_cap",
        ],
    )
    for (kind, reason), count in (tallies or {}).items():
        connection.execute(
            "INSERT INTO collection_run_tally VALUES (?, 'azure-retail', ?, ?, ?)",
            [run_id, kind, reason, count],
        )
