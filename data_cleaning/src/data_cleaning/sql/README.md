# ELT SQL Methods

This directory stores reproducible SQL used by the ELT process.

Reproducibility note:
- `sandbox_refresh_all_review.sql` runs
  `python data_cleaning/src/data_cleaning/sql/build_crosswalk_csvs.py` before SQL.
- That step parses crosswalk XLSX inputs and writes deterministic CSV output to
  `flat_data/in/raw_data/crosswalks/generated/school_identity_crosswalk_prepared.csv`.

- `ref_canonical_tables.sql`: creates canonical reference tables in `ref` schema
  (gender, race, ethnicity, staff position, NCES locale).
- `ref_geo_tables.sql`: creates geographic reference tables in `ref` schema
  (population groups, norm scopes, opportunity levels, domain/subdomain/metric taxonomy).
- `sandbox_dim_school_info_review_v2.sql`: builds typed school info review table with
  parsed state IDs, canonical NCES locale mapping, and backfill rows from teacher
  demographics where school-year combinations are missing in school draft data.
- `sandbox_geo_review_models.sql`: builds Alabama geographic review tables
  (tract dims, tract geo facts, and strict school-county bridge via
  hand-match NCES resolution, exact county-name match, and deterministic
  district-to-county crosswalk fallback).
  This script loads `flat_data/in/raw_data/crosswalks/district_to_county.csv` via
  `\copy`, so run it from the repository root. It also builds school outcomes
  review facts from `flat_data/in/raw_data/al_sch24_v1.csv`.
- `build_crosswalk_csvs.py`: parses crosswalk XLSX files and materializes
  deterministic CSVs for SQL loading. It also writes
  `flat_data/in/raw_data/crosswalks/generated/school_identity_crosswalk_audit.csv`
  with reproducibility/coverage checks.
- `sandbox_teacher_review_models.sql`: builds the review teacher long fact table
  using `ref` canonical mappings and school dimension keys.
- `sandbox_student_review_models.sql`: builds the review student long fact table
  using `ref` canonical mappings and school dimension keys.
- `sandbox_core_remaining_tables.sql`: builds and populates typed review tables
  for the remaining core-aligned facts (accountability, edunomics, teacher
  effectiveness, teacher experience), including dedupe and school-key joins.
- `sandbox_refresh_all_review.sql`: convenience runner that executes all review
  SQL scripts in sequence.
- `core_load_review_to_core.sql`: creates core long tables (if needed) and upserts
  reviewed sandbox school/student/teacher long data into `core`.
- `core_load_geo_to_core.sql`: creates core geographic tables (if needed) and
  upserts reviewed sandbox geo dims/facts and school-county bridge into `core`.
- `geo_strict_null_report.sql`: reports matched rows and strict-null rows for
  school-county mapping from sandbox/core bridge tables.

Run these scripts in order when bootstrapping a new environment.
