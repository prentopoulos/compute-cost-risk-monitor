# Walkthrough script

A tour of the demo in 1 minute 58 seconds, on invented prices. The video has on-screen captions
and no voice. It was recorded on 2026-10-15 from the synthetic demo at 1920 × 1080.

To record it again, build the demo with
`uv run --locked python -m compute_cost_risk_monitor.demo --serve`, then follow the shots below.
Every figure comes from the demo database, dated 12 October 2026 09:00 UTC. Record before
19 October 2026 09:00 UTC, when the demo starts to show STALE.

| Time | Screen | Action | Caption |
| --- | --- | --- | --- |
| 0:00 | Title card | — | Compute Cost & Risk Monitor · What will renting GPUs cost, and what if prices change? · Demo on invented prices — not Azure list prices |
| 0:06 | Workload cost | Highlight the status line | This is the dashboard. The yellow label means these are invented demo prices. |
| 0:13 | Workload cost | Highlight the sidebar | On the left, pick the GPU, the machine size, the pricing and the region. |
| 0:20 | Workload cost | Highlight the key figures | The answer comes first: 32 H100 GPUs for 720 hours cost USD 276,480. |
| 0:26 | Workload cost | Highlight the what-if grid | The grid shows what happens if prices move, from half price to double. |
| 0:33 | Workload cost | Highlight +69,120 (+25%, 32 GPUs) | If prices rise 25%, this job costs USD 69,120 more. It's a what-if, not a forecast. |
| 0:41 | Workload cost | Highlight the EXCL. line | Under every cost, a line lists what it doesn't include, like storage and taxes. |
| 0:48 | Workload cost | Type 64 into GPUs and press Enter | Change the job and every number updates. |
| 0:53 | Workload cost | Highlight the new key figures | Change the job and every number updates: 64 GPUs cost USD 552,960. |
| 1:03 | Comparable groups | Open the tab; highlight the group | Prices are only compared for the same kind of machine. |
| 1:08 | Comparable groups | Highlight the across-regions table | Across 5 regions, this machine lists from 12 to 15 USD per GPU-hour. |
| 1:19 | Data quality | Open the tab; highlight the Azure table | The data-quality tab shows how fresh the prices are, and counts every row that was set aside, with the reason. |
| 1:30 | Market brief | Show `docs/brief/brief.md`; highlight the bottom line | Each snapshot also gets an AI-powered market brief, with the bottom line first. |
| 1:36 | Market brief | — | Claude drafts the text, and code calculates every figure in it. |
| 1:44 | Market brief | Scroll to the last line; highlight it | A second, independent check recalculates every figure before the brief is saved. |
| 1:51 | End card | — | Compute Cost & Risk Monitor · GPU cost and price-risk dashboard · AI-powered market brief · github.com/prentopoulos/compute-cost-risk-monitor · Invented prices — not Azure list prices |

Checked figures: 32 × 720 × 12.0000 = 276,480; 25% of that is 69,120;
64 × 720 × 12.0000 = 552,960. The five regions list this size from 12.0000 to 15.0000 USD per
GPU-hour.
