# Detailed Build Plan

## Objective

Recreate the EFLT database structure on a remote Postgres instance using medallion-aligned schemas while preserving current API compatibility at the table/column level.

## Decisions

- Keep unchanged schemas: `sandbox`, `ref`
- Rename curated layers:
  - `raw` -> `bronze`
  - `staging` -> `silver`
  - `core` -> `gold`
- Move materialized views into `platinum`

## Reliability Design

1. Versioned SQL migrations in source control
2. Migration checksums validated at runtime
3. Migration journal table in `pipeline_meta`
4. Deterministic ordering by filename prefix
5. Dry-run mode before apply
6. Idempotent DDL where possible (`IF NOT EXISTS`)

## Implementation Phases

1. Bootstrap
   - Create `apps/pipeline` with `uv` project config
   - Add CLI runner and migration engine
2. Foundation Migrations
   - Create schemas and migration journal
   - Create canonical `ref` tables
3. Data-Layer Migrations
   - Create `bronze` and `silver` structures
   - Create `sandbox` review/imputation structures
   - Create `gold` serving structures and views
   - Create `platinum` materialized views and indexes
4. ETL Lineage Documentation
   - Record pipeline step manifest from flat files to serving layers
5. Validation
   - `status` shows applied/pending
   - `plan` shows execution order
   - `apply --dry-run` confirms no writes

## Complexity Assessment (Sandbox and Ref)

- `ref` should be maintained permanently:
  - low object count
  - high data integrity value
  - direct API dependency for metadata filters
- `sandbox` should be maintained now, but as transient/non-serving:
  - useful for review gates and imputation traceability
  - higher object/dependency count, so enforce cleanup policy by run lifecycle

## Next Implementation Step (Not Yet Included)

- Add executable ETL orchestrator subcommands to load from `flat_data/in/raw_data` into `silver`, produce review outputs in `sandbox`, then publish to `gold` and refresh `platinum`.
