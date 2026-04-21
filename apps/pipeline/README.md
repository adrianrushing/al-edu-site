# EFLT Pipeline

This app recreates the database structure for the medallion architecture on a remote Postgres instance.

## Schema Model

- `bronze`: raw landing and file manifests
- `silver`: standardized staging tables
- `gold`: serving tables for API and analytics
- `platinum`: materialized views for heavy query paths
- `sandbox`: review/transient ETL layer (unchanged)
- `ref`: canonical reference dictionaries (unchanged)

## Setup

```bash
cp apps/pipeline/.env.example apps/pipeline/.env
```

Fill in `DATABASE_URL` with the remote DB URL you bootstrap.

## Commands

```bash
uv sync --project apps/pipeline
uv run --project apps/pipeline python -m pipeline.cli status
uv run --project apps/pipeline python -m pipeline.cli plan
uv run --project apps/pipeline python -m pipeline.cli apply
uv run --project apps/pipeline python -m pipeline.cli sources
uv run --project apps/pipeline python -m pipeline.cli ingest-bronze
```

Dry run:

```bash
uv run --project apps/pipeline python -m pipeline.cli apply --dry-run
```

`--dry-run` is offline and does not connect to the database.

Optional raw source override:

```bash
uv run --project apps/pipeline python -m pipeline.cli sources --raw-data-dir /path/to/raw_data
uv run --project apps/pipeline python -m pipeline.cli ingest-bronze --raw-data-dir /path/to/raw_data
```

## Scope

- This app creates structure and can ingest raw CSV sources into the bronze layer.
- `ingest-bronze` always appends a new run and does not truncate prior bronze runs.
- It does not modify local/dev DB unless `DATABASE_URL` points there.

## Migration Metadata

- Tracks execution in `pipeline_meta.schema_migrations`
- Records migration name, checksum, and timestamp
- Prevents silent drift when migration files change
