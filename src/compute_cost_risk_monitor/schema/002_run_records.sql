-- Schema version 2: insert-only run records, written once when a run ends.
-- Version-1 tables stay unchanged. DuckDB 1.5.6 cannot add constrained columns or CHECK
-- constraints, and refuses to update a collection_run row that a raw_response row
-- references, so a run's final status, counts and repeats arrive as whole new rows.
-- Reasons and stop reasons are free text, not CHECK lists, because a CHECK list cannot be
-- extended by a later migration.

CREATE TABLE collection_run_summary (
    run_id              VARCHAR PRIMARY KEY,
    source              VARCHAR NOT NULL,
    requests            INTEGER NOT NULL CHECK (requests >= 0),
    pages_parsed        INTEGER NOT NULL CHECK (pages_parsed >= 0),
    failed_requests     INTEGER NOT NULL CHECK (failed_requests >= 0),
    throttled           INTEGER NOT NULL CHECK (throttled >= 0),
    items_seen          INTEGER NOT NULL CHECK (items_seen >= 0),
    observations_stored INTEGER NOT NULL CHECK (observations_stored >= 0),
    repeats             INTEGER NOT NULL CHECK (repeats >= 0),
    out_of_scope        INTEGER NOT NULL CHECK (out_of_scope >= 0),
    rejected            INTEGER NOT NULL CHECK (rejected >= 0),
    stop_reason         VARCHAR NOT NULL CHECK (length(stop_reason) > 0),
    -- Every request either yielded a parsed page or failed; 429s are failures.
    CHECK (pages_parsed + failed_requests = requests),
    CHECK (throttled <= failed_requests),
    -- Every item seen lands in exactly one bucket.
    CHECK (items_seen = observations_stored + repeats + out_of_scope + rejected),
    FOREIGN KEY (run_id, source) REFERENCES collection_run (run_id, source)
);

CREATE TABLE collection_run_tally (
    run_id      VARCHAR NOT NULL,
    source      VARCHAR NOT NULL,
    -- rejected: why items were not stored; flagged: conditions noted on stored items or pages.
    kind        VARCHAR NOT NULL CHECK (kind IN ('rejected', 'flagged')),
    reason      VARCHAR NOT NULL CHECK (length(reason) > 0),
    occurrences INTEGER NOT NULL CHECK (occurrences > 0),
    PRIMARY KEY (run_id, kind, reason),
    FOREIGN KEY (run_id, source) REFERENCES collection_run (run_id, source)
);

CREATE TABLE observation_repeat (
    -- Where the later copy appeared.
    response_id        VARCHAR NOT NULL,
    item_index         INTEGER NOT NULL CHECK (item_index >= 0),
    source             VARCHAR NOT NULL,
    item_key           VARCHAR NOT NULL,
    -- The observation stored from the first copy.
    first_retrieved_at TIMESTAMPTZ NOT NULL,
    same_price         BOOLEAN NOT NULL,
    same_fields        BOOLEAN NOT NULL,
    PRIMARY KEY (response_id, item_index),
    FOREIGN KEY (response_id, source) REFERENCES raw_response (response_id, source),
    FOREIGN KEY (source, item_key, first_retrieved_at)
        REFERENCES price_observation (source, item_key, retrieved_at)
);
