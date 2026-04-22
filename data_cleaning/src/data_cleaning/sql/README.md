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
- `build_school_hierarchy_polars.py`: Polars-based school hierarchy loader that
  reads from `staging.stg_school_edunomics` as source of truth and writes
  `sandbox.dim_state_review`, `sandbox.dim_district_review`,
  `sandbox.dim_school_review`, `sandbox.bridge_school_year_review`, and
  compatibility table `sandbox.dim_school_info_review`.
  `sandbox.dim_state_review` uses `department_name` for the state education
  agency label (for AL: `Alabama State Department of Education`).
- `sandbox_geo_review_models.sql`: builds Alabama geographic review tables
  (tract dims, tract geo facts, and strict school-county bridge via
  hand-match NCES resolution, exact county-name match, and deterministic
  district-to-county crosswalk fallback).
  This script loads `flat_data/in/raw_data/crosswalks/district_to_county.csv` via
  `\copy`, so run it from the repository root. It also builds school outcomes
  review facts from `flat_data/in/raw_data/al_sch24_v1.csv`.
- `load_school_outcomes_polars.py`: Polars ETL that reads
  `flat_data/in/raw_data/al_sch24_v1.csv`, writes
  `staging.stg_school_outcomes` (all requested string columns), and writes
  typed review table `sandbox.fact_school_outcomes_demographic_review` for
  efficient loading to `core.fact_school_outcomes_demographic`.
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
  Also builds educator credentials review + explicit degree-type wide pivots and
  graduation rate review + all-demographic school-year wide review tables.
- `sandbox_refresh_all_review.sql`: convenience runner that executes review steps
  in sequence, including the Polars school hierarchy loader and the school
  outcomes demographic ETL.
- `core_load_review_to_core.sql`: creates core long tables (if needed) and upserts
  reviewed sandbox school/student/teacher long data into `core`.
  Also upserts `core.fact_educator_credentials_wide` and
  `core.fact_graduation_rate_wide` from sandbox review-wide tables.
  Also loads hierarchy dims (`core.dim_state`, `core.dim_district`,
  `core.dim_school`, `core.bridge_school_year`) and keeps
  `core.dim_school_info` as compatibility layer.
- `core_load_geo_to_core.sql`: creates core geographic tables (if needed) and
  upserts reviewed sandbox geo dims/facts and school-county bridge into `core`.
  Includes county-level geo tables (`core.fact_geo_population_county`,
  `core.fact_geo_opportunity_county`) and join helper views:
  `core.vw_school_year_geo_bridge`, `core.vw_school_year_geo_population`,
  `core.vw_school_year_geo_opportunity`, and
  `core.vw_school_year_geo_context` (single-row school-year context for
  school + district + state + county joins).
- `core_create_school_year_profiles.sql`: creates joined serving views for
  modeling and analytics at school-year and district-year grains:
  `core.vw_school_year_full_profile`, `core.vw_district_year_features`, and
  `core.vw_district_year_profile`.
- `core_create_trainable_option3_compare.sql`: creates option-3 trainable
  enrichment views with both district COI variants and leakage-safe as-of
  funding fills:
  `core.vw_district_county_weights`, `core.vw_district_coi_features`, and
  `core.vw_school_year_full_profile_trainable_option3`.
- `core_create_accountability_all_pivot_mv.sql`: creates
  `core.mv_fact_accountability_all_pivot` at school-year grain with only
  `All Grades/All Gender/All Race/All Ethnicity/All SubPopulation` rows,
  mapping student + academic achievement into `achievement` and pivoting
  accountability indicators into `achievement`, `graduation_rate`,
  `academic_growth`, `absenteeism`, `ccr`, and `elp`.
- `qa_core_school_year_joinability.sql`: read-only validation checks for
  school-year joinability and usefulness, including cardinality, fanout,
  county mapping quality, year overlap, and district-year sufficiency.
- `geo_strict_null_report.sql`: reports matched rows and strict-null rows for
  school-county mapping from sandbox/core bridge tables.

Run these scripts in order when bootstrapping a new environment:

1. `sandbox_refresh_all_review.sql`
2. `core_load_review_to_core.sql`
3. `core_load_geo_to_core.sql`
4. `core_create_accountability_all_pivot_mv.sql`
5. `core_create_school_year_profiles.sql`
6. `core_create_trainable_option3_compare.sql`
7. Optional QA: `qa_core_school_year_joinability.sql`
