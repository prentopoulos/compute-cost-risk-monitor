# Synthetic fixtures

Every file here is **synthetic**. The values are invented to exercise the schema and later the
parsers and rules; they are not real Azure or marketplace prices. No real source data is
committed to this repository (Phase 1 design D4).

- `azure_retail_page.json`: shaped like one page of the Azure Retail Prices API response
  (`Items`, `NextPageLink`, `Count`). It follows the field names in Microsoft's documentation.
  IDs are zero-filled placeholders and prices are round invented numbers.
- `azure_demo.json`: a synthetic Azure-shaped snapshot (one page, labelled synthetic, with an
  `observed_at` time) for the dashboard demo, AppTest flows and PR screenshots. Size names are
  real Azure names so the packaged GPU map applies; every price and ID is invented. Ingested
  with `uv run python -m compute_cost_risk_monitor.synthetic`, it holds:
  - H100 ×8 pay-as-you-go in 5 regions (a summary that is not thin) and Spot in 3 (thin);
  - a US East Spot price equal to its pay-as-you-go price;
  - a UK South Spot size with no pay-as-you-go listing in its region, so the calculator's
    Spot to pay-as-you-go fallback shows "not computed" (Phase 5 design D12);
  - two T4 sizes in one US East group, and single-price T4 and A100 groups;
  - an unmapped size (MI300X `ND96is`) and a Windows row.
- `azure_items.json`: one invented Azure-shaped item plus labelled cases (normal, edge,
  deliberately failing), each with its known answer for the collector's row rules.
- `marketplace_offers.json`: marketplace-style offers for the hybrid plan's marketplace-only
  rules (duplicates, re-listing by machine, thin samples). The provider is fictional.
- `marketplace/snapshot-1.json` … `snapshot-3.json`: three consecutive synthetic marketplace
  snapshots (one day apart) with known answers for the Phase 3 rules:
  - machine M-01 lists two 1-GPU H100 offers on day 1 (a machine duplicate) and a 2-GPU offer
    (a different group);
  - M-01 is re-listed on day 2 under a new offer ID at a new price (a change, not a new offer);
  - M-03's price changes on day 2; M-04 is absent on days 2 and 3 ("not listed", dated day 2);
  - M-11 is absent on day 2 and back on day 3 under a new offer ID; M-06 is new on day 3;
  - the RTX 4090 Spot group is thin (fewer than 5 machines);
  - an unknown GPU name, a VRAM mismatch and a reservation are excluded with their reasons.
- `azure_history/snapshot-1.json` … `snapshot-3.json`: three synthetic Azure-shaped snapshots,
  one week apart, for the Phase 6 end-to-end known-answer test (design D17). Every price and ID
  is invented. The answers below were worked out by hand, not by the code under test.

  | Item | Listing | Snapshot 1 (2026-09-01 09:00 UTC) | 2 (09-08) | 3 (09-15) |
  |---|---|---|---|---|
  | A | H100 ×8 `Standard_ND96isr_H100_v5`, eastus, pay-as-you-go | 96 | 96 | 104 |
  | B | the same size, westeurope, pay-as-you-go | 100 | 100 | absent |
  | C | T4 `Standard_NC4as_T4_v3`, eastus, pay-as-you-go | 0.6 | absent | absent |
  | D | the same size, westeurope, pay-as-you-go | 0.7 | absent | 0.75 |
  | E | H100 ×8, eastus, Spot | 40 | 40 | 40 |
  | F | T4, southcentralus, unit `1/Day` | 14.4 | 14.4 | 14.4 |

  - **Rows:**
    - Snapshot 1 stores 6 observations, snapshots 2 and 3 store 4 each, and none is rejected.
    - F is excluded as `unit_not_hourly` every time and is never converted. The rest are
      normalized: 5, 3 and 3 rows.
  - **USD/GPU-hour:**
    - A: 12.0, then 13.0 in snapshot 3;
    - B: 12.5;
    - C: 0.6;
    - D: 0.7, then 0.75;
    - E: 5.0.
  - **History as of snapshot 3:**
    - one change since snapshot 2: A from 96 to 104 (12.0 to 13.0). E and F are unchanged.
    - D returns at a new price, which is not a change, because it was missing from snapshot 2.
      Nothing changed between snapshots 1 and 2.
    - B is absent once (unconfirmed): missing from 3, last seen in 2.
    - C is not listed, dated at snapshot 2 (2026-09-08 09:00 UTC), last seen in 1.
    - D is neither absent nor a change.
  - **Quality report for snapshot 3:**
    - 4 observations: 3 normalized, 1 `unit_not_hourly`;
    - 3 region groups (H100 ×8 eastus pay-as-you-go and Spot, T4 ×1 westeurope
      pay-as-you-go), each a single list price;
    - 3 cross-region summaries, all thin;
    - changes 1, absent once 1, not listed 1;
    - nothing unmapped, rejected, out of scope or repeated.
  - **Stale** (snapshot 3 started 2026-09-15 09:00 UTC):
    - not stale as of 2026-09-17 09:00, and not stale at exactly 2026-09-22 09:00:00;
    - stale at 09:00:01.
  - **Workload:** 32 GPUs × 720 h (4 VMs, 23,040 GPU-hours) on group A in snapshot 3, at 13.0
    USD/GPU-hour, costs 299,520.

    | Scenario | USD/GPU-hour | Change | Cost | Exposure |
    |---|---|---|---|---|
    | Decline −25% | 9.75 | −3.25 | 224,640 | −74,880 (lower expense) |
    | Increase +25% | 16.25 | +3.25 | 374,400 | +74,880 |
    | PROJECT example +$0.50 | 13.5 | +0.5 | 311,040 | +11,520 |
    | Spike +100% | 26.0 | +13.0 | 599,040 | +299,520 |

    A budget of 11,520 gives a headroom of 0.5 USD/GPU-hour.
  - **Spot:** the same workload on E (5.0 USD/GPU-hour) costs 115,200.

    | Scenario | USD/GPU-hour | Exposure |
    |---|---|---|
    | Decline | 3.75 | −28,800 |
    | Increase | 6.25 | +28,800 |
    | Example | 5.5 | +11,520 |
    | Spike | 10.0 | +115,200 |
    | Spot to pay-as-you-go fallback (A at 13.0) | 13.0 | +184,320, cost 299,520 |

    No Spot row is above 13.0, so none carries a note.
