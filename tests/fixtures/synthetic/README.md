# Synthetic fixtures

Every file here is **synthetic**. The values are invented to exercise the schema and later the
parsers and rules; they are not real Azure or marketplace prices. No real source data is
committed to this repository (Phase 1 design D4).

- `azure_retail_page.json`: shaped like one page of the Azure Retail Prices API response
  (`Items`, `NextPageLink`, `Count`). It follows the field names in Microsoft's documentation.
  IDs are zero-filled placeholders and prices are round invented numbers.
- `marketplace_offers.json`: marketplace-style offers for the hybrid plan's marketplace-only
  rules (duplicates, re-listing by machine, thin samples). The provider is fictional.
