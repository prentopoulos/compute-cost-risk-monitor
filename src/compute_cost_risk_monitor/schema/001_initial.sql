-- Schema version 1: source-neutral price observations with per-source detail.
-- Rules enforced here: provenance on every price, finite positive USD prices, no duplicate
-- (source, item, retrieval time), known labels and rental types, missing values stay NULL,
-- and an observation's source always matches the run that collected it.
-- Enumerations are CHECK lists so a later migration can extend them. DuckDB orders NaN
-- above every number, so every numeric check uses isfinite() as well as a range.

CREATE TABLE schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL,
    description VARCHAR NOT NULL
);

CREATE TABLE collection_run (
    run_id              VARCHAR PRIMARY KEY,
    source              VARCHAR NOT NULL
        CHECK (source IN ('azure-retail', 'synthetic-marketplace')),
    data_label          VARCHAR NOT NULL
        CHECK (data_label IN ('synthetic', 'recorded', 'live')),
    started_at          TIMESTAMPTZ NOT NULL,
    finished_at         TIMESTAMPTZ,
    status              VARCHAR NOT NULL
        CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    code_version        VARCHAR,
    schema_version      INTEGER NOT NULL REFERENCES schema_version (version),
    dependency_versions JSON,
    request_params      JSON,
    notes               VARCHAR,
    -- Synthetic marketplace data can never pass as recorded or live.
    CHECK (source <> 'synthetic-marketplace' OR data_label = 'synthetic'),
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    UNIQUE (run_id, source)
);

CREATE TABLE raw_response (
    response_id  VARCHAR PRIMARY KEY,
    run_id       VARCHAR NOT NULL,
    source       VARCHAR NOT NULL,
    seq          INTEGER NOT NULL CHECK (seq >= 0),
    file_path    VARCHAR NOT NULL,
    sha256       VARCHAR NOT NULL CHECK (regexp_full_match(sha256, '[0-9a-f]{64}')),
    byte_length  BIGINT NOT NULL CHECK (byte_length >= 0),
    request_url  VARCHAR NOT NULL,
    http_status  INTEGER,
    requested_at TIMESTAMPTZ NOT NULL,
    received_at  TIMESTAMPTZ,
    item_count   INTEGER CHECK (item_count IS NULL OR item_count >= 0),
    parse_status VARCHAR NOT NULL
        CHECK (parse_status IN ('parsed', 'failed', 'not_parsed')),
    error        VARCHAR,
    UNIQUE (run_id, seq),
    UNIQUE (response_id, source),
    -- The response's source is its run's source.
    FOREIGN KEY (run_id, source) REFERENCES collection_run (run_id, source)
);

CREATE TABLE price_observation (
    source       VARCHAR NOT NULL
        CHECK (source IN ('azure-retail', 'synthetic-marketplace')),
    item_key     VARCHAR NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    response_id  VARCHAR NOT NULL,
    rental_type  VARCHAR NOT NULL
        CHECK (rental_type IN
            ('on_demand', 'spot', 'reservation', 'savings_plan', 'dev_test', 'other')),
    region       VARCHAR NOT NULL,
    -- The source's price for the whole item (one VM-hour, one offer-hour), never per GPU.
    price        DOUBLE NOT NULL CHECK (isfinite(price) AND price > 0),
    currency     VARCHAR NOT NULL CHECK (currency = 'USD'),
    price_unit   VARCHAR NOT NULL,
    -- Unknown until mapped; NULL, never zero or a placeholder.
    gpu_model    VARCHAR,
    gpu_count    DOUBLE CHECK (gpu_count IS NULL OR (isfinite(gpu_count) AND gpu_count > 0)),
    PRIMARY KEY (source, item_key, retrieved_at),
    -- Lets detail and derived rows prove they agree with the observation.
    UNIQUE (source, item_key, retrieved_at, region, rental_type),
    UNIQUE (source, item_key, retrieved_at, region, price),
    -- The observation's source is its response's (and so its run's) source.
    FOREIGN KEY (response_id, source) REFERENCES raw_response (response_id, source)
);

CREATE TABLE azure_retail_price (
    source                  VARCHAR NOT NULL CHECK (source = 'azure-retail'),
    item_key                VARCHAR NOT NULL,
    retrieved_at            TIMESTAMPTZ NOT NULL,
    meter_id                VARCHAR NOT NULL,
    sku_id                  VARCHAR NOT NULL,
    arm_sku_name            VARCHAR,
    arm_region_name         VARCHAR NOT NULL,
    location                VARCHAR,
    price_type              VARCHAR NOT NULL,
    retail_price            DOUBLE NOT NULL
        CHECK (isfinite(retail_price) AND retail_price > 0),
    unit_price              DOUBLE
        CHECK (unit_price IS NULL OR (isfinite(unit_price) AND unit_price >= 0)),
    unit_of_measure         VARCHAR NOT NULL,
    effective_start_date    TIMESTAMPTZ,
    product_id              VARCHAR,
    product_name            VARCHAR,
    sku_name                VARCHAR,
    meter_name              VARCHAR,
    service_name            VARCHAR,
    service_family          VARCHAR,
    is_primary_meter_region BOOLEAN,
    reservation_term        VARCHAR,
    tier_minimum_units      DOUBLE
        CHECK (tier_minimum_units IS NULL
               OR (isfinite(tier_minimum_units) AND tier_minimum_units >= 0)),
    savings_plan            JSON,
    PRIMARY KEY (source, item_key, retrieved_at),
    -- Region and price must be the observation's region and price.
    FOREIGN KEY (source, item_key, retrieved_at, arm_region_name, retail_price)
        REFERENCES price_observation (source, item_key, retrieved_at, region, price)
);

CREATE TABLE marketplace_offer (
    source          VARCHAR NOT NULL CHECK (source = 'synthetic-marketplace'),
    item_key        VARCHAR NOT NULL,
    retrieved_at    TIMESTAMPTZ NOT NULL,
    offer_id        VARCHAR NOT NULL,
    machine_id      VARCHAR NOT NULL,
    gpu_name_listed VARCHAR NOT NULL,
    num_gpus        INTEGER NOT NULL CHECK (num_gpus > 0),
    gpu_vram_gb     DOUBLE
        CHECK (gpu_vram_gb IS NULL OR (isfinite(gpu_vram_gb) AND gpu_vram_gb > 0)),
    country_code    VARCHAR
        CHECK (country_code IS NULL OR regexp_full_match(country_code, '[A-Z]{2}')),
    PRIMARY KEY (source, item_key, retrieved_at),
    FOREIGN KEY (source, item_key, retrieved_at)
        REFERENCES price_observation (source, item_key, retrieved_at)
);

CREATE TABLE gpu_sku_map (
    mapping_version VARCHAR NOT NULL,
    arm_sku_name    VARCHAR NOT NULL,
    gpu_model       VARCHAR NOT NULL,
    gpu_form_factor VARCHAR,
    gpu_vram_gb     DOUBLE
        CHECK (gpu_vram_gb IS NULL OR (isfinite(gpu_vram_gb) AND gpu_vram_gb > 0)),
    gpu_count       DOUBLE NOT NULL CHECK (isfinite(gpu_count) AND gpu_count > 0),
    source_url      VARCHAR NOT NULL,
    notes           VARCHAR,
    PRIMARY KEY (mapping_version, arm_sku_name)
);

CREATE TABLE rule_set (
    rule_version VARCHAR PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL,
    description  VARCHAR NOT NULL,
    parameters   JSON NOT NULL
);

CREATE TABLE normalized_price (
    source           VARCHAR NOT NULL
        CHECK (source IN ('azure-retail', 'synthetic-marketplace')),
    item_key         VARCHAR NOT NULL,
    retrieved_at     TIMESTAMPTZ NOT NULL,
    rule_version     VARCHAR NOT NULL REFERENCES rule_set (rule_version),
    region           VARCHAR NOT NULL,
    rental_type      VARCHAR NOT NULL
        CHECK (rental_type IN
            ('on_demand', 'spot', 'reservation', 'savings_plan', 'dev_test', 'other')),
    -- NULL only when the row is excluded (excluded_reason says why).
    usd_per_gpu_hour DOUBLE
        CHECK (usd_per_gpu_hour IS NULL
               OR (isfinite(usd_per_gpu_hour) AND usd_per_gpu_hour > 0)),
    gpu_model        VARCHAR,
    gpu_count        DOUBLE CHECK (gpu_count IS NULL OR (isfinite(gpu_count) AND gpu_count > 0)),
    -- The SKU mapping used, when the source needs one (Azure); both or neither.
    mapping_version  VARCHAR,
    arm_sku_name     VARCHAR,
    exclusions       VARCHAR NOT NULL,
    excluded_reason  VARCHAR,
    PRIMARY KEY (source, item_key, retrieved_at, rule_version),
    -- Region and rental type must be the observation's.
    FOREIGN KEY (source, item_key, retrieved_at, region, rental_type)
        REFERENCES price_observation (source, item_key, retrieved_at, region, rental_type),
    FOREIGN KEY (mapping_version, arm_sku_name)
        REFERENCES gpu_sku_map (mapping_version, arm_sku_name),
    CHECK ((mapping_version IS NULL) = (arm_sku_name IS NULL)),
    -- A normalized row has a price and a group key; an excluded row has a reason instead.
    CHECK ((excluded_reason IS NULL) = (usd_per_gpu_hour IS NOT NULL)),
    CHECK (excluded_reason IS NOT NULL OR (gpu_model IS NOT NULL AND gpu_count IS NOT NULL))
);
