# ALSDE Staging Ingest Runbook

This runbook appends canonical ALSDE CSVs into existing staging tables, with
checkpointed/idempotent behavior and post-load QA.

## Scope

In-scope target tables:

- `staging.stg_school_accountability`
- `staging.stg_student_demographics`
- `staging.stg_teacher_demographics`
- `staging.stg_teacher_experience`

Out-of-scope for this runbook:

- educator credentials (requires dedicated raw staging table)
- graduation rate (requires dedicated raw staging table)

## Canonical file rules

Only ingest canonical yearly files from
`apps/pipeline/src/pipeline/alsde_supporting_data/downloaded`:

- `alsde_accountability_YYYY-YYYY.csv`
- `alsde_student_demographics_YYYY-YYYY.csv`
- `alsde_educator_demographics_YYYY-YYYY.csv`
- `alsde_educator_experience_YYYY-YYYY.csv`

Never ingest raw exports/shards in this flow:

- `SupportingData_*.csv`
- `*_city.csv`, `*_county.csv`, short prefix files like `_al.csv`
- `*.crdownload`, `.org.chromium.*`

## 1) Preflight: remote DB reachability

```bash
uv run --project apps/pipeline python - <<'PY'
import psycopg
url='postgresql://eflt_etl:1qaz2wsx3edc@127.0.0.1:15432/eflt'
with psycopg.connect(url, connect_timeout=10) as conn:
    with conn.cursor() as cur:
        cur.execute('select current_user, current_database()')
        print(cur.fetchone())
PY
```

## 2) Build + validate ingest manifest

```bash
uv run --project apps/pipeline python -m pipeline.alsde_supporting_data.build_staging_ingest_manifest \
  --output-json apps/pipeline/.staging_ingest_manifest.json \
  --log-level INFO
```

## 3) Rebuild yearly student demographics files

```bash
uv run --project apps/pipeline alsde-student-demographics-combine --log-level INFO
```

## 4) Append loads (existing loaders)

### Accountability -> `staging.stg_school_accountability`

```bash
uv run --project apps/pipeline python -m pipeline.alsde_supporting_data.load_accountability_remote \
  --file-pattern "alsde_accountability_*.csv" \
  --database-url "postgresql://eflt_etl:1qaz2wsx3edc@127.0.0.1:15432/eflt" \
  --batch-size 20000 \
  --log-level INFO
```

### Student demographics -> `staging.stg_student_demographics`

```bash
uv run --project apps/pipeline alsde-student-demographics-load \
  --database-url "postgresql://eflt_etl:1qaz2wsx3edc@127.0.0.1:15432/eflt" \
  --batch-size 20000 \
  --log-level INFO
```

### Teacher demographics / experience

Use your dedicated teacher loaders when available, or equivalent chunked COPY
loader with the same checkpoint/idempotency pattern.

## 5) Post-load QA SQL

Run on the target DB after all loads complete.

```sql
-- Row deltas by year
SELECT year, COUNT(*)
FROM staging.stg_school_accountability
GROUP BY 1
ORDER BY 1;

SELECT year, COUNT(*)
FROM staging.stg_student_demographics
GROUP BY 1
ORDER BY 1;

SELECT year, COUNT(*)
FROM staging.stg_teacher_demographics
GROUP BY 1
ORDER BY 1;

SELECT year, COUNT(*)
FROM staging.stg_teacher_experience
GROUP BY 1
ORDER BY 1;

-- Source file distribution
SELECT _source_file, COUNT(*)
FROM staging.stg_student_demographics
GROUP BY 1
ORDER BY 2 DESC;

-- Key null checks
SELECT
  SUM(CASE WHEN year IS NULL OR year = '' THEN 1 ELSE 0 END) AS null_year,
  SUM(CASE WHEN system IS NULL OR system = '' THEN 1 ELSE 0 END) AS null_system,
  SUM(CASE WHEN school IS NULL OR school = '' THEN 1 ELSE 0 END) AS null_school
FROM staging.stg_student_demographics;
```

## 6) Idempotency check

Immediately rerun step 4. Inserted rows should be zero or near-zero (only true
new source rows).

## 7) Downstream SQL sequence (when ready)

```bash
psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/sandbox_refresh_all_review.sql
psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/core_load_review_to_core.sql
psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/core_load_geo_to_core.sql
psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/core_create_accountability_all_pivot_mv.sql
```
