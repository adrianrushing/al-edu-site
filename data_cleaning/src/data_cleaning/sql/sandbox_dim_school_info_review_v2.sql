-- Build review-ready school dimension in sandbox with typed state IDs,
-- canonical NCES locale mapping, and normalized naming keys.

DROP TABLE IF EXISTS sandbox.dim_school_info_review_v2;

CREATE TABLE sandbox.dim_school_info_review_v2 (
    school_key             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_year_label      VARCHAR(9) NOT NULL,
    school_year_start      SMALLINT NOT NULL,
    school_year_end        SMALLINT,
    state_code             CHAR(2) NOT NULL,
    state_dist_id          INTEGER,
    state_school_id        INTEGER,
    nces_admin_id          BIGINT,
    nces_geo_id            BIGINT,
    census_id              BIGINT,
    nces_id                BIGINT,
    dist_name              TEXT NOT NULL,
    school_name            TEXT NOT NULL,
    nces_locale_key        SMALLINT NOT NULL REFERENCES ref.nces_locale_canonical(nces_locale_key),
    nces_locale_type       VARCHAR(20),
    nces_locale_subtype    VARCHAR(20),
    nces_charter           BOOLEAN,
    nces_magnet            BOOLEAN,
    nces_address           TEXT,
    nces_city              VARCHAR(120),
    nces_zip               VARCHAR(15),
    source_nces_locale     TEXT,
    source_state_dist_id   TEXT,
    source_state_school_id TEXT,
    _source_file           TEXT,
    _ingested_at           TIMESTAMP,
    _created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dim_school_review_v2 UNIQUE (school_year_label, dist_name, school_name)
);

WITH ranked AS (
  SELECT d.*, ROW_NUMBER() OVER (
    PARTITION BY d.year, d.district_name, d.school_name
    ORDER BY d._ingested_at DESC NULLS LAST, d._source_file DESC NULLS LAST
  ) AS rn
  FROM sandbox.dim_school_info_draft d
  WHERE d.year IS NOT NULL
    AND d.district_name IS NOT NULL
    AND d.school_name IS NOT NULL
),
base AS (
  SELECT
    d.*,
    regexp_replace(trim(d.district_name), '[[:space:]]+', ' ', 'g') AS dist_name_clean,
    regexp_replace(trim(d.school_name), '[[:space:]]+', ' ', 'g') AS school_name_clean,
    lower(regexp_replace(trim(d.district_name), '[[:space:]]+', ' ', 'g')) AS dist_name_norm,
    lower(regexp_replace(trim(d.school_name), '[[:space:]]+', ' ', 'g')) AS school_name_norm,
    CASE
      WHEN d.nces_locale ~ '^[0-9]{2}-' THEN split_part(d.nces_locale, '-', 1)::int
      WHEN lower(trim(coalesce(d.nces_locale,''))) IN ('city: midsize','city: mid-size') THEN 12
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'city: small' THEN 13
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'suburb: large' THEN 21
      WHEN lower(trim(coalesce(d.nces_locale,''))) IN ('suburb: midsize','suburb: mid-size') THEN 22
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'suburb: small' THEN 23
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'town: fringe' THEN 31
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'town: distant' THEN 32
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'town: remote' THEN 33
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'rural: fringe' THEN 41
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'rural: distant' THEN 42
      WHEN lower(trim(coalesce(d.nces_locale,''))) = 'rural: remote' THEN 43
      ELSE NULL
    END AS locale_code
  FROM ranked d
  WHERE d.rn = 1
),
canonical_names AS (
  SELECT dist_name_norm, school_name_norm, dist_name_clean, school_name_clean
  FROM (
    SELECT
      dist_name_norm,
      school_name_norm,
      dist_name_clean,
      school_name_clean,
      COUNT(*) AS variant_count,
      ROW_NUMBER() OVER (
        PARTITION BY dist_name_norm, school_name_norm
        ORDER BY COUNT(*) DESC, dist_name_clean, school_name_clean
      ) AS rn
    FROM base
    GROUP BY dist_name_norm, school_name_norm, dist_name_clean, school_name_clean
  ) t
  WHERE rn = 1
)
INSERT INTO sandbox.dim_school_info_review_v2 (
    school_year_label,
    school_year_start,
    school_year_end,
    state_code,
    state_dist_id,
    state_school_id,
    nces_admin_id,
    nces_geo_id,
    census_id,
    nces_id,
    dist_name,
    school_name,
    nces_locale_key,
    nces_locale_type,
    nces_locale_subtype,
    nces_charter,
    nces_magnet,
    nces_address,
    nces_city,
    nces_zip,
    source_nces_locale,
    source_state_dist_id,
    source_state_school_id,
    _source_file,
    _ingested_at
)
SELECT
    b.year AS school_year_label,
    CASE
      WHEN b.year ~ '^[0-9]{4}-[0-9]{4}$' THEN split_part(b.year, '-', 1)::smallint
      WHEN b.year ~ '^[0-9]{4}$' THEN b.year::smallint
      ELSE NULL
    END AS school_year_start,
    CASE
      WHEN b.year ~ '^[0-9]{4}-[0-9]{4}$' THEN split_part(b.year, '-', 2)::smallint
      ELSE NULL
    END AS school_year_end,
    'AL'::char(2) AS state_code,
    CASE
      WHEN b.state_dist_id ~ '^AL-[0-9]+$' THEN split_part(b.state_dist_id, '-', 2)::int
      WHEN b.state_dist_id ~ '^[0-9]+$' THEN b.state_dist_id::int
      ELSE NULL
    END AS state_dist_id,
    CASE
      WHEN b.state_school_id ~ '^AL-[0-9]+-[0-9]+$' THEN split_part(b.state_school_id, '-', 3)::int
      WHEN b.state_school_id ~ '^[0-9]+$' THEN b.state_school_id::int
      ELSE NULL
    END AS state_school_id,
    CASE WHEN b.nces_admin_id ~ '^[0-9]+$' THEN b.nces_admin_id::bigint END AS nces_admin_id,
    CASE WHEN b.nces_geo_id ~ '^[0-9]+$' THEN b.nces_geo_id::bigint END AS nces_geo_id,
    CASE WHEN b.census_id ~ '^[0-9]+$' THEN b.census_id::bigint END AS census_id,
    CASE WHEN b.nces_id ~ '^[0-9]+$' THEN b.nces_id::bigint END AS nces_id,
    cn.dist_name_clean AS dist_name,
    cn.school_name_clean AS school_name,
    coalesce(loc.nces_locale_key, unk.nces_locale_key) AS nces_locale_key,
    coalesce(loc.locale_group, unk.locale_group) AS nces_locale_type,
    coalesce(loc.locale_subtype, unk.locale_subtype) AS nces_locale_subtype,
    CASE
      WHEN lower(coalesce(b.nces_charter, '')) IN ('yes', 'y', 'true', 't', '1', '1-yes') THEN TRUE
      WHEN lower(coalesce(b.nces_charter, '')) IN ('no', 'n', 'false', 'f', '0', '2-no') THEN FALSE
      ELSE NULL
    END AS nces_charter,
    CASE
      WHEN lower(coalesce(b.nces_magnet, '')) IN ('yes', 'y', 'true', 't', '1', '1-yes') THEN TRUE
      WHEN lower(coalesce(b.nces_magnet, '')) IN ('no', 'n', 'false', 'f', '0', '2-no') THEN FALSE
      ELSE NULL
    END AS nces_magnet,
    NULLIF(b.nces_address, '') AS nces_address,
    NULLIF(b.nces_city, '') AS nces_city,
    NULLIF(b.nces_zip, '') AS nces_zip,
    b.nces_locale AS source_nces_locale,
    b.state_dist_id AS source_state_dist_id,
    b.state_school_id AS source_state_school_id,
    b._source_file,
    b._ingested_at
FROM base b
JOIN canonical_names cn
  ON cn.dist_name_norm = b.dist_name_norm
 AND cn.school_name_norm = b.school_name_norm
LEFT JOIN ref.nces_locale_canonical loc
  ON loc.locale_code = b.locale_code
CROSS JOIN LATERAL (
  SELECT nces_locale_key, locale_group, locale_subtype
  FROM ref.nces_locale_canonical
  WHERE is_unknown = TRUE
  LIMIT 1
) unk;

-- Add school-year rows present in teacher demographics but absent in school draft
-- using normalized district/school matching to prevent duplicates.
WITH unk AS (
  SELECT nces_locale_key, locale_group, locale_subtype
  FROM ref.nces_locale_canonical
  WHERE is_unknown = TRUE
  LIMIT 1
), missing_school_year AS (
  SELECT DISTINCT
    t.year::smallint AS yr,
    regexp_replace(trim(t.system), '[[:space:]]+', ' ', 'g') AS dist_name,
    regexp_replace(trim(t.school), '[[:space:]]+', ' ', 'g') AS school_name,
    lower(regexp_replace(trim(t.system), '[[:space:]]+', ' ', 'g')) AS dist_name_norm,
    lower(regexp_replace(trim(t.school), '[[:space:]]+', ' ', 'g')) AS school_name_norm
  FROM sandbox.impute_teacher_demographics t
  WHERE NOT EXISTS (
    SELECT 1
    FROM sandbox.dim_school_info_review_v2 s
    WHERE s.school_year_start = t.year::smallint
      AND lower(s.dist_name) = lower(regexp_replace(trim(t.system), '[[:space:]]+', ' ', 'g'))
      AND lower(s.school_name) = lower(regexp_replace(trim(t.school), '[[:space:]]+', ' ', 'g'))
  )
)
INSERT INTO sandbox.dim_school_info_review_v2 (
  school_year_label,
  school_year_start,
  school_year_end,
  state_code,
  state_dist_id,
  state_school_id,
  nces_admin_id,
  nces_geo_id,
  census_id,
  nces_id,
  dist_name,
  school_name,
  nces_locale_key,
  nces_locale_type,
  nces_locale_subtype,
  nces_charter,
  nces_magnet,
  nces_address,
  nces_city,
  nces_zip,
  source_nces_locale,
  source_state_dist_id,
  source_state_school_id,
  _source_file,
  _ingested_at
)
SELECT
  concat(m.yr::text, '-', (m.yr + 1)::text),
  m.yr,
  (m.yr + 1)::smallint,
  'AL'::char(2),
  NULL, NULL, NULL, NULL, NULL, NULL,
  m.dist_name,
  m.school_name,
  u.nces_locale_key,
  u.locale_group,
  u.locale_subtype,
  NULL, NULL, NULL, NULL, NULL,
  NULL, NULL, NULL,
  'impute_teacher_demographics',
  now()::timestamp
FROM missing_school_year m
CROSS JOIN unk u
ON CONFLICT (school_year_label, dist_name, school_name) DO NOTHING;

-- Prevent case/whitespace duplicates at business key level.
CREATE UNIQUE INDEX uq_dim_school_review_v2_norm
  ON sandbox.dim_school_info_review_v2 (
    school_year_label,
    lower(regexp_replace(trim(dist_name), '[[:space:]]+', ' ', 'g')),
    lower(regexp_replace(trim(school_name), '[[:space:]]+', ' ', 'g'))
  );

CREATE INDEX idx_school_info_review_v2_year_name
  ON sandbox.dim_school_info_review_v2 (school_year_start, dist_name, school_name);
CREATE INDEX idx_school_info_review_v2_state_ids
  ON sandbox.dim_school_info_review_v2 (state_code, state_dist_id, state_school_id);
CREATE INDEX idx_school_info_review_v2_locale
  ON sandbox.dim_school_info_review_v2 (nces_locale_key);
