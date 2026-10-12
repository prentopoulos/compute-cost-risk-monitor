# Synthetic fixtures

Every file here is **synthetic**. The values are invented to exercise the schema and later the
parsers and rules; they are not real Azure or marketplace prices. No real source data is
committed to this repository (Phase 1 design D4).

- `azure_retail_page.json`: shaped like one page of the Azure Retail Prices API response
  (`Items`, `NextPageLink`, `Count`). It follows the field names in Microsoft's documentation.
  IDs are zero-filled placeholders and prices are round invented numbers.
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
