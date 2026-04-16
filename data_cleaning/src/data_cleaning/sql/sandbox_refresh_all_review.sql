-- Refresh all review tables in sandbox (run with psql)
-- Example:
--   psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/sandbox_refresh_all_review.sql

\! python data_cleaning/src/data_cleaning/sql/build_crosswalk_csvs.py

\i data_cleaning/src/data_cleaning/sql/ref_canonical_tables.sql
\i data_cleaning/src/data_cleaning/sql/ref_geo_tables.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_dim_school_info_review_v2.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_geo_review_models.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_teacher_review_models.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_student_review_models.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_core_remaining_tables.sql
