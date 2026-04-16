-- Build student long review model in sandbox from imputed student table.
-- Assumes:
--   1) ref canonical tables exist
--   2) sandbox.impute_student_demographics_long exists

DROP TABLE IF EXISTS sandbox.fact_student_demographics_long_review;

CREATE TABLE sandbox.fact_student_demographics_long_review (
    year               SMALLINT NOT NULL,
    dist_name          TEXT NOT NULL,
    school_name        TEXT NOT NULL,
    grade              VARCHAR(30),
    gender             TEXT NOT NULL,
    ethnicity          TEXT NOT NULL,
    race               TEXT NOT NULL,
    sub_population     TEXT,
    demographic_count  NUMERIC(14,2),
    _created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_student_long_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, grade, gender, ethnicity, race, sub_population)
);

WITH mapped AS (
    SELECT
        t.year::smallint AS year,
        trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        t.grade,
        g.canonical_value AS gender,
        e.canonical_value AS ethnicity,
        r.canonical_value AS race,
        t.sub_population,
        t.count::numeric(14,2) AS demographic_count,
        ROW_NUMBER() OVER (
            PARTITION BY
                t.year::smallint,
                lower(trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g'))),
                t.grade,
                g.canonical_value,
                e.canonical_value,
                r.canonical_value,
                t.sub_population
            ORDER BY t.year DESC
        ) AS rn
    FROM sandbox.impute_student_demographics_long t
    JOIN ref.gender_canonical g
      ON g.normalized_value = lower(trim(regexp_replace(t.gender, '[[:space:]]+', ' ', 'g')))
    JOIN ref.ethnicity_canonical e
      ON e.normalized_value = lower(trim(regexp_replace(t.ethnicity, '[[:space:]]+', ' ', 'g')))
    JOIN ref.race_canonical r
      ON r.normalized_value = lower(trim(regexp_replace(
        CASE
          WHEN t.race = 'all_races' THEN 'All Race'
          WHEN t.race = 'asian' THEN 'Asian'
          WHEN t.race = 'black_or_african_american' THEN 'Black or African American'
          WHEN t.race = 'american_indian_alaska_native' THEN 'American Indian/Alaska Native'
          WHEN t.race = 'native_hawaiian_pacific_islander' THEN 'Native Hawaiian/Pacific Islander'
          WHEN t.race = 'white' THEN 'White'
          WHEN t.race = 'two_or_more_races' THEN 'Two or more races'
          ELSE t.race
        END,
        '[[:space:]]+', ' ', 'g'
      )))
)
INSERT INTO sandbox.fact_student_demographics_long_review (
    year, dist_name, school_name, grade, gender, ethnicity, race, sub_population,
    demographic_count
)
SELECT
    year, dist_name, school_name, grade, gender, ethnicity, race, sub_population,
    demographic_count
FROM mapped
WHERE rn = 1;

CREATE INDEX idx_student_long_review_school_year
  ON sandbox.fact_student_demographics_long_review (year, dist_name, school_name);
