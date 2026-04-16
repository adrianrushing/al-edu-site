-- Build teacher long review model in sandbox from imputed teacher table.
-- Assumes:
--   1) ref canonical tables exist
--   2) sandbox.impute_teacher_demographics exists

DROP TABLE IF EXISTS sandbox.fact_teacher_demographics_long_review;

CREATE TABLE sandbox.fact_teacher_demographics_long_review (
    year               SMALLINT NOT NULL,
    dist_name          TEXT NOT NULL,
    school_name        TEXT NOT NULL,
    gender             TEXT NOT NULL,
    race               TEXT NOT NULL,
    ethnicity          TEXT NOT NULL,
    sub_population     TEXT NOT NULL,
    demographic_count  DOUBLE PRECISION,
    demographic_rate   DOUBLE PRECISION,
    imputed_flag       BOOLEAN NOT NULL DEFAULT FALSE,
    imputation_method  TEXT,
    _created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_teacher_long_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, gender, race, ethnicity, sub_population)
);

WITH mapped AS (
    SELECT
        t.year::smallint AS year,
        trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        g.canonical_value AS gender,
        r.canonical_value AS race,
        e.canonical_value AS ethnicity,
        sp.canonical_value AS sub_population,
        t.demographic_count,
        t.demographic_rate,
        coalesce(t.imputed_flag, false) AS imputed_flag,
        t.imputation_method,
        t._ingested_at,
        t._source_file,
        ROW_NUMBER() OVER (
            PARTITION BY
                t.year::smallint,
                lower(trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g'))),
                g.canonical_value,
                r.canonical_value,
                e.canonical_value,
                sp.canonical_value
            ORDER BY t._ingested_at DESC NULLS LAST, t._source_file DESC NULLS LAST
        ) AS rn
    FROM sandbox.impute_teacher_demographics t
    JOIN ref.gender_canonical g
      ON g.normalized_value = lower(trim(regexp_replace(t.gender, '[[:space:]]+', ' ', 'g')))
    JOIN ref.race_canonical r
      ON r.normalized_value = lower(trim(regexp_replace(t.race, '[[:space:]]+', ' ', 'g')))
    JOIN ref.ethnicity_canonical e
      ON e.normalized_value = lower(trim(regexp_replace(t.ethnicity, '[[:space:]]+', ' ', 'g')))
    JOIN ref.staff_position_canonical sp
      ON sp.normalized_value = lower(trim(regexp_replace(t.sub_population, '[[:space:]]+', ' ', 'g')))
)
INSERT INTO sandbox.fact_teacher_demographics_long_review (
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    demographic_count, demographic_rate, imputed_flag, imputation_method
)
SELECT
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    demographic_count, demographic_rate, imputed_flag, imputation_method
FROM mapped
WHERE rn = 1;

CREATE INDEX idx_teacher_long_review_school_year
  ON sandbox.fact_teacher_demographics_long_review (year, dist_name, school_name);
