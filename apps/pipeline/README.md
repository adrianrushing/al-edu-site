# EFLT Pipeline (Legacy)

The medallion architecture components (`bronze`, `silver`, `platinum`, and
`pipeline_meta`) have been removed from this repository.

The `pipeline` package is kept only as a compatibility placeholder so the
existing project layout and script entry point remain valid.

Running the CLI now reports that the medallion commands were removed:

```bash
uv run --project apps/pipeline python -m pipeline.cli
```

## Accountability CSV remote load

To load downloaded ALSDE accountability exports directly into the remote staging
table (without local Docker DB hop), run:

```bash
uv run --project apps/pipeline python -m pipeline.alsde_supporting_data.load_accountability_remote
```

The loader reads `*_Accountability.csv` from
`apps/pipeline/src/pipeline/alsde_supporting_data/downloaded`, normalizes header
names to lowercase snake_case, keeps values unchanged, and writes to
`staging.stg_school_accountability` in chunked inserts with checkpoint resume.

## Student demographics yearly combine + remote load

Combine partitioned student demographics exports into yearly files:

```bash
uv run --project apps/pipeline alsde-student-demographics-combine
```

Load combined yearly files to remote staging with deduplicated inserts:

```bash
uv run --project apps/pipeline alsde-student-demographics-load
```

Target table: `staging.stg_student_demographics`.

Build and validate a canonical staging-ingest manifest:

```bash
uv run --project apps/pipeline alsde-staging-manifest
```

Detailed ingest checklist/runbook:

- `apps/pipeline/src/pipeline/alsde_supporting_data/STAGING_INGEST_RUNBOOK.md`

Single phased loader for all existing staging targets:

```bash
uv run --project apps/pipeline alsde-staging-load-all --log-level INFO
```

## New sources staging load (credentials + graduation rate)

Load only the two new source families that do not map to existing historical
staging loaders:

```bash
uv run --project apps/pipeline alsde-staging-new-sources-load \
  --expected-port 15432 \
  --log-level INFO
```

This command:

- Targets only `alsde_educator_credentials_YYYY-YYYY.csv` and
  `alsde_graduation_rate_YYYY-YYYY.csv`.
- Verifies the connection URL port is `15432` before writing.
- Preserves source markers like `*` and `~` as raw text in staging.
- Appends with deduplicated insert behavior and source metadata
  (`_source_file`, `_ingested_at`).
