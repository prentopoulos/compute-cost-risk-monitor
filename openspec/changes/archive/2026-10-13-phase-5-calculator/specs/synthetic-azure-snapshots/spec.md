## MODIFIED Requirements

### Requirement: Synthetic Azure snapshot files
A synthetic Azure snapshot SHALL be a JSON file shaped like one Azure Retail Prices API page
(`Items`, with `NextPageLink` null) that also holds `"_label": "synthetic"` and an `observed_at`
time with a time zone. Its prices SHALL be invented; its size names MAY be real Azure names so
the packaged GPU map applies. A file without the synthetic label, without a valid `observed_at`,
or without a non-empty `Items` list SHALL be refused before anything is written, and so SHALL a
file none of whose items passes the row rules.

The committed file `tests/fixtures/synthetic/azure_demo.json` SHALL cover at least:
- a region group with several sizes and one with a single list price;
- a thin cross-region summary and one with at least 5 regions;
- a Spot price equal to the pay-as-you-go price of the same size;
- a Spot size with no pay-as-you-go listing in its region;
- an unmapped size and a Windows row.

#### Scenario: Unlabelled file refused
- **WHEN** an Azure-shaped file lacks `"_label": "synthetic"`
- **THEN** ingest raises an error and writes nothing

#### Scenario: Nothing stored is refused
- **WHEN** every item in a synthetic Azure file is out of scope or rejected
- **THEN** ingest raises an error and stores no run

#### Scenario: Demo file covers the dashboard cases
- **WHEN** `azure_demo.json` is ingested and normalized into an empty database
- **THEN** its snapshot has a multi-size region group, a single-price group, a thin and a non-thin summary, a Spot row equal to its pay-as-you-go price, a Spot row whose size has no pay-as-you-go listing in its region, a row excluded as `unmapped_sku` and a row excluded as `windows`
