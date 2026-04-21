CREATE TABLE IF NOT EXISTS bronze.raw_csv_records (
    run_id UUID NOT NULL,
    source_path TEXT NOT NULL,
    dataset_key TEXT NOT NULL,
    row_number BIGINT NOT NULL,
    row_data JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, source_path, row_number)
);

CREATE INDEX IF NOT EXISTS idx_bronze_raw_csv_records_run_id
    ON bronze.raw_csv_records (run_id);

CREATE INDEX IF NOT EXISTS idx_bronze_raw_csv_records_dataset_key
    ON bronze.raw_csv_records (dataset_key);

CREATE INDEX IF NOT EXISTS idx_bronze_raw_csv_records_source_path
    ON bronze.raw_csv_records (source_path);
