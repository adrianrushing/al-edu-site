# v_two lightweight refresh

This directory contains a minimal refresh path for ALSDE-backed sandbox + core tables.

## Files

- `impute_student_demographics_light.py`: lightweight student imputation to `sandbox.impute_student_demographics_long`
- `sandbox_refresh_all_review.sql`: rebuilds sandbox review tables from staging + imputed student table
- `core_load_review_to_core.sql`: refreshes core from sandbox using school-key mapping
- `validate_refresh.sql`: compares sandbox/core year coverage and 2025 row counts
- `run_refresh.py`: optional runner script for end-to-end execution

## Run

```bash
uv run --project data_cleaning python data_cleaning/src/data_cleaning/v_two/run_refresh.py \
  --database-url "postgresql://eflt_etl:1qaz2wsx3edc@127.0.0.1:15432/eflt"
```
