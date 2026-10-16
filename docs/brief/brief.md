# Market brief

**SYNTHETIC DATA — NOT AZURE LIST PRICES** · snapshot 2026-10-12 09:00 UTC (run synthetic-20261012T090000Z-2b4972) · AS OF 2026-10-12 09:00 UTC

Invented prices for demonstration, in the shape of Azure's API.

## Bottom line

32 H100 NVLink 80GB GPUs, run as 4 VMs of ND96isr H100 v5 for 720 hours, cost USD 276,480.00 at the lowest listed pay-as-you-go price for this GPU and count, in US East at 12.0000 USD/GPU-h. Across 5 regions the lowest listed prices run from 12.0000 to 15.0000 USD/GPU-h, putting the same workload at USD 276,480.00 to 345,600.00. A contingency of USD 69,120.00 covers a +25% list-price move, and USD 138,240.00 covers a +50% move.

*This compares across regions.*

*Scenario calculation, not a forecast. Round sensitivities chosen by judgement, not calibrated to history or to any model.*

*Not priced: disks and storage, egress, public IPs, licences, taxes, negotiated discounts, reservations and savings plans, Spot eviction risk, capacity and quota.*

## Changes since the previous snapshot

2 listed prices changed between 2026-10-05 09:00 UTC and 2026-10-12 09:00 UTC, each for ND96isr H100 v5 on Linux in US East. The pay-as-you-go price rose from 88.00 to 96.00 USD/VM-h (11.0000 to 12.0000 USD/GPU-h), and the Spot price rose from 88.00 to 96.00 USD/VM-h (11.0000 to 12.0000 USD/GPU-h).

- US East · ND96isr H100 v5 · pay-as-you-go · linux: 88.00 → 96.00 USD/VM-h (11.0000 → 12.0000 USD/GPU-h).
- US East · ND96isr H100 v5 · Spot · linux: 88.00 → 96.00 USD/VM-h (11.0000 → 12.0000 USD/GPU-h).

## Absences

1 listing is absent once and unconfirmed, missing since 2026-10-12 09:00 UTC after last appearing at 2026-10-05 09:00 UTC. 1 listing is not listed, missing since 2026-10-05 09:00 UTC after last appearing at 2026-09-28 09:00 UTC.

- EU West · NC24ads A100 v4 · pay-as-you-go · linux: absent once (unconfirmed) since 2026-10-12 09:00 UTC, last seen 2026-10-05 09:00 UTC.
- EU West · NC8as T4 v3 · pay-as-you-go · linux: not listed since 2026-10-05 09:00 UTC, last seen 2026-09-28 09:00 UTC.

## Groups per GPU

The latest snapshot holds 11 region groups across 3 GPU variants, and 10 of them have a single list price. H100 NVLink 80GB accounts for 8 groups, all 8 with a single list price; T4 16GB has 2 groups with 1 single-priced, and A100 PCIe 80GB has 1 group with 1 single-priced.

| GPU | Region groups | Single list price |
|---|---:|---:|
| A100 PCIe 80GB | 1 | 1 |
| H100 NVLink 80GB | 8 | 8 |
| T4 16GB | 2 | 1 |

## Spot against pay-as-you-go

2 of 3 H100 NVLink 80GB Spot listings have the same size on pay-as-you-go in the same region; 1 equals it and 0 are above it. A Spot price of 12.0000 USD/GPU-h matches its pay-as-you-go price of 12.0000, a share of 100.0%, while another at 5.0000 sits at 40.0% of 12.5000; a further Spot listing at 6.0000 has no pay-as-you-go pair.

| Region | Size | Spot, USD/GPU-h | Pay-as-you-go, USD/GPU-h | Spot as % of pay-as-you-go |
|---|---|---:|---:|---:|
| US East | ND96isr H100 v5 | 12.0000 | 12.0000 | 100.0 |
| UK South | ND96isr H100 v5 | 6.0000 | no pay-as-you-go listing for this size in this region | — |
| EU West | ND96isr H100 v5 | 5.0000 | 12.5000 | 40.0 |

*Each line crosses rental types (Spot → pay-as-you-go): same size, same region.*

## Across regions

There are 4 cross-region summaries, and 3 of them are thin, from fewer than 5 regions. H100 NVLink 80GB pay-as-you-go across 5 regions runs 12.0000 to 15.0000 USD/GPU-h with a median of 13.0000, while its Spot group across 3 regions runs 5.0000 to 12.0000 with a median of 6.0000. T4 16GB across 2 regions runs 0.6000 to 0.7000 with a median of 0.6500, and A100 PCIe 80GB in 1 region lists at 3.8000, with median 3.8000 and high 3.8000.

| GPU | Pricing | Regions | Lowest | Median | Highest | Labels |
|---|---|---:|---:|---:|---:|---|
| A100 PCIe 80GB × 1 | pay-as-you-go | 1 | 3.8000 | 3.8000 | 3.8000 | crosses regions · thin |
| H100 NVLink 80GB × 8 | pay-as-you-go | 5 | 12.0000 | 13.0000 | 15.0000 | crosses regions |
| H100 NVLink 80GB × 8 | Spot | 3 | 5.0000 | 6.0000 | 12.0000 | crosses regions · thin |
| T4 16GB × 1 | pay-as-you-go | 2 | 0.6000 | 0.6500 | 0.7000 | crosses regions · thin |

*This compares across regions. Each region counts once, at its lowest listed price. The median is a statistic, not a listed price.*

## Data quality

The latest snapshot holds 14 observations; 12 are compared and the rest are excluded, each with its reason: 1 as an unmapped size and 1 as Windows, with 1 size absent from the GPU map. The data spans 3 succeeded snapshots over 14 days, and a snapshot counts as stale after 7 days.

- Observations: 14, of which 12 are compared.
- Excluded as `unmapped_sku`: 1.
- Excluded as `windows`: 1.
- Sizes not in the GPU map: 1.
- Region groups: 11, 10 with a single list price.
- Cross-region summaries: 4, 3 thin.
- Changes since the previous snapshot: 2.
- Absent once (unconfirmed): 1; not listed: 1.
- Stale: no, as of 2026-10-12 09:00 UTC (stale after 7 days).

*Sample too thin for trends: 3 snapshots over 14 days.*

---

GPU map: contains material from Microsoft Learn, © Microsoft, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

Prose drafted by claude-opus-5-5 (prompt v3); every number placed and checked by code.

## Records

| Fact | Run | Item | Retrieved | Raw-response SHA-256 |
|---|---|---|---|---|
| `snap_time` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `as_of` | stated input or fixed rule | | | |
| `bl_gpus` | stated input or fixed rule | | | |
| `bl_variant` | stated input or fixed rule | | | |
| `bl_vms` | derived from `bl_gpus` | | | |
| `bl_size` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_hours` | stated input or fixed rule | | | |
| `bl_cost` | derived from `bl_gpus`, `bl_hours`, `bl_price` | | | |
| `bl_region` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_price` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_regions` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_regions` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000103\|SYNTH0103/0001\|southcentralus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_regions` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000105\|SYNTH0105/0001\|swedencentral\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_regions` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000102\|SYNTH0102/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_regions` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000104\|SYNTH0104/0001\|westus3\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000105\|SYNTH0105/0001\|swedencentral\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `bl_cost_min` | derived from `bl_gpus`, `bl_hours`, `bl_min` | | | |
| `bl_cost_max` | derived from `bl_gpus`, `bl_hours`, `bl_max` | | | |
| `bl_c25` | derived from `bl_gpus`, `bl_hours`, `bl_price`, `bl_c25_move` | | | |
| `bl_c25_move` | stated input or fixed rule | | | |
| `bl_c50` | derived from `bl_gpus`, `bl_hours`, `bl_price`, `bl_c50_move` | | | |
| `bl_c50_move` | stated input or fixed rule | | | |
| `n_changes` | derived from `prev_time`, `snap_time` | | | |
| `prev_time` | synthetic-20261005T090000Z-101e6e |  |  | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `chg_1_before` | synthetic-20261005T090000Z-101e6e | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-05 09:00 UTC | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `chg_1_after` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `chg_1_before_gpu` | synthetic-20261005T090000Z-101e6e | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-05 09:00 UTC | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `chg_1_after_gpu` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `chg_2_before` | synthetic-20261005T090000Z-101e6e | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-05 09:00 UTC | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `chg_2_after` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `chg_2_before_gpu` | synthetic-20261005T090000Z-101e6e | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-05 09:00 UTC | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `chg_2_after_gpu` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_absent_once` | derived from `snap_time` | | | |
| `abs_1_since` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `abs_1_seen` | synthetic-20261005T090000Z-101e6e |  |  | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `n_not_listed` | derived from `snap_time` | | | |
| `abs_2_since` | synthetic-20261005T090000Z-101e6e |  |  | 101e6e611bd8c5f8af678e71347a147bb0a058218fd6c261cf6c864652162dc8 |
| `abs_2_seen` | synthetic-20260928T090000Z-f69c3e |  |  | f69c3e5397031c96203cd54f69b82a536ccdf736f66eb69cbf064ca2421fccf3 |
| `n_groups` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_variants` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_single` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `grp_2_n` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `grp_2_single` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `grp_3_n` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `grp_3_single` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `grp_1_n` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `grp_1_single` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_spot_paired` | derived from `snap_time` | | | |
| `n_spot` | derived from `snap_time` | | | |
| `n_spot_equal` | derived from `snap_time` | | | |
| `n_spot_above` | derived from `snap_time` | | | |
| `spot_1_spot` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `spot_1_payg` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `spot_1_ratio` | derived from `spot_1_spot`, `spot_1_payg` | | | |
| `spot_3_spot` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000107\|SYNTH0107/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `spot_3_ratio` | derived from `spot_3_spot`, `spot_3_payg` | | | |
| `spot_3_payg` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000102\|SYNTH0102/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `spot_2_spot` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000114\|SYNTH0114/0001\|uksouth\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_summaries` | derived from `snap_time` | | | |
| `n_thin` | derived from `snap_time`, `thin_below` | | | |
| `thin_below` | stated input or fixed rule | | | |
| `reg_2_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000103\|SYNTH0103/0001\|southcentralus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000105\|SYNTH0105/0001\|swedencentral\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000102\|SYNTH0102/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000104\|SYNTH0104/0001\|westus3\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000103\|SYNTH0103/0001\|southcentralus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000105\|SYNTH0105/0001\|swedencentral\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000102\|SYNTH0102/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000104\|SYNTH0104/0001\|westus3\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000103\|SYNTH0103/0001\|southcentralus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000105\|SYNTH0105/0001\|swedencentral\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000102\|SYNTH0102/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000104\|SYNTH0104/0001\|westus3\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000101\|SYNTH0101/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000103\|SYNTH0103/0001\|southcentralus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000105\|SYNTH0105/0001\|swedencentral\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000102\|SYNTH0102/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_2_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000104\|SYNTH0104/0001\|westus3\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000114\|SYNTH0114/0001\|uksouth\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000107\|SYNTH0107/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000114\|SYNTH0114/0001\|uksouth\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000107\|SYNTH0107/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000114\|SYNTH0114/0001\|uksouth\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000107\|SYNTH0107/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000106\|SYNTH0106/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000114\|SYNTH0114/0001\|uksouth\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_3_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000107\|SYNTH0107/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_ND96isr_H100_v5 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000108\|SYNTH0108/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000110\|SYNTH0110/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000108\|SYNTH0108/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000110\|SYNTH0110/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000108\|SYNTH0108/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000110\|SYNTH0110/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000108\|SYNTH0108/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_4_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000110\|SYNTH0110/0001\|westeurope\|Consumption\|\|0.0\|USD\|Standard_NC4as_T4_v3 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_1_n` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000111\|SYNTH0111/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC24ads_A100_v4 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_1_min` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000111\|SYNTH0111/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC24ads_A100_v4 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_1_median` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000111\|SYNTH0111/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC24ads_A100_v4 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `reg_1_max` | synthetic-20261012T090000Z-2b4972 | 00000000-0000-0000-0000-000000000111\|SYNTH0111/0001\|eastus\|Consumption\|\|0.0\|USD\|Standard_NC24ads_A100_v4 | 2026-10-12 09:00 UTC | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `q_obs` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `q_normalized` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `q_reason_2` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `q_reason_3` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `q_unmapped` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_snapshots` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `n_days` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
| `stale_days` | synthetic-20261012T090000Z-2b4972 |  |  | 2b4972683a3825143fb34b0bc78703244a9e4401d293e82dc8b6acee6e405c6a |
