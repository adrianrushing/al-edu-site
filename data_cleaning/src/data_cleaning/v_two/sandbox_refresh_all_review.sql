\set ON_ERROR_STOP on

-- Minimal sandbox refresh for ALSDE-fed review tables.
-- Student data is expected to be precomputed into sandbox.impute_student_demographics_long
-- by impute_student_demographics_light.py (or promoted equivalent).

\i data_cleaning/src/data_cleaning/sql/ref_canonical_tables.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_teacher_review_models.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_student_review_models.sql
\i data_cleaning/src/data_cleaning/sql/sandbox_core_remaining_tables.sql
