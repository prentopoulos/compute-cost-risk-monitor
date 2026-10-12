# Reference data

`gpu_sku_map_v1.csv` maps Azure GPU VM sizes (`armSkuName`) to their GPU variant, per-GPU memory
and GPU count. It is map version `gpu-map-v1`.

- **Source:** Microsoft Learn VM size pages only, one URL per row, read by hand on 2026-10-12.
  There is no scraper (phase-3-normalization design D14).
- **Rule:** a size is listed only when its exact ARM name appears on the cited page. Sizes that
  Learn does not name exactly stay unmapped and are counted as `unmapped_sku`, never guessed
  (design D9).
- **Labels:** `<model>[ <form factor>] <memory>GB`, in Learn's wording, which says "NVLink" and
  never "SXM" (design D3).
- **Counts:** fractions such as `1/4` mark partial-GPU sizes, which are not compared in v1.
- **No prices:** the file holds documentation facts only, and no Azure Retail Prices data.

## Attribution

Contains material from [Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/overview),
© Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The
material was adapted: values were copied from size tables and descriptions into this CSV.

A change to any row is a new map version. Rows stored in a database under `gpu-map-v1` are never
rewritten.
