-- Build review-ready school hierarchy in sandbox:
-- state -> district -> school + school-year bridge.
-- Also materialize compatibility table: sandbox.dim_school_info_review.

DROP TABLE IF EXISTS sandbox.dim_school_info_review_v2;
DROP TABLE IF EXISTS sandbox.dim_school_info_review;
DROP TABLE IF EXISTS sandbox.bridge_school_year_review;
DROP TABLE IF EXISTS sandbox.dim_school_review;
DROP TABLE IF EXISTS sandbox.dim_district_review;
DROP TABLE IF EXISTS sandbox.dim_state_review;

CREATE TABLE sandbox.dim_state_review (
    state_key    BIGINT PRIMARY KEY,
    state_code   CHAR(2) NOT NULL UNIQUE,
    state_name   TEXT NOT NULL,
    _created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sandbox.dim_district_review (
    district_key           BIGINT PRIMARY KEY,
    state_key              BIGINT NOT NULL REFERENCES sandbox.dim_state_review(state_key),
    state_code             CHAR(2) NOT NULL,
    district_name          TEXT NOT NULL,
    district_name_norm     TEXT NOT NULL,
    state_dist_id          INTEGER,
    nces_admin_id          BIGINT,
    source_state_dist_id   TEXT,
    _created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dim_district_review UNIQUE (state_code, district_name_norm)
);

CREATE TABLE sandbox.dim_school_review (
    school_key             BIGINT PRIMARY KEY,
    district_key           BIGINT NOT NULL REFERENCES sandbox.dim_district_review(district_key),
    state_code             CHAR(2) NOT NULL,
    school_name            TEXT NOT NULL,
    school_name_norm       TEXT NOT NULL,
    state_school_id        INTEGER,
    nces_geo_id            BIGINT,
    census_id              BIGINT,
    nces_id                BIGINT,
    nces_charter           BOOLEAN,
    nces_magnet            BOOLEAN,
    nces_address           TEXT,
    nces_city              VARCHAR(120),
    nces_zip               VARCHAR(15),
    source_state_school_id TEXT,
    _created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dim_school_review UNIQUE (district_key, school_name_norm)
);

CREATE TABLE sandbox.bridge_school_year_review (
    school_key           BIGINT NOT NULL REFERENCES sandbox.dim_school_review(school_key),
    school_year_label    VARCHAR(9) NOT NULL,
    school_year_start    SMALLINT NOT NULL,
    school_year_end      SMALLINT,
    nces_locale_key      SMALLINT NOT NULL REFERENCES ref.nces_locale_canonical(nces_locale_key),
    nces_locale_type     VARCHAR(20),
    nces_locale_subtype  VARCHAR(20),
    source_nces_locale   TEXT,
    _source_file         TEXT,
    _ingested_at         TIMESTAMP,
    _created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_bridge_school_year_review PRIMARY KEY (school_key, school_year_start)
);

CREATE TABLE sandbox.dim_school_info_review (
    school_key             BIGINT NOT NULL,
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
    CONSTRAINT pk_dim_school_info_review PRIMARY KEY (school_key, school_year_start),
    CONSTRAINT uq_dim_school_review_flat UNIQUE (school_year_label, dist_name, school_name)
);

CREATE TEMP TABLE _school_rows_prepared AS
WITH unk AS (
    SELECT nces_locale_key, locale_group, locale_subtype
    FROM ref.nces_locale_canonical
    WHERE is_unknown = TRUE
    LIMIT 1
),
crosswalk_best AS (
    SELECT
        c.ncessch,
        c.school_name AS school_name_xw,
        c.system_name AS dist_name_xw,
        ROW_NUMBER() OVER (
            PARTITION BY c.ncessch
            ORDER BY c.priority DESC, c.match_method, c.school_name, c.system_name
        ) AS rn
    FROM sandbox.ref_school_identity_crosswalk_review c
),
crosswalk_unique AS (
    SELECT
        b.ncessch,
        NULLIF(trim(regexp_replace(b.school_name_xw, '[[:space:]]+', ' ', 'g')), '') AS school_name_xw,
        NULLIF(trim(regexp_replace(b.dist_name_xw, '[[:space:]]+', ' ', 'g')), '') AS dist_name_xw
    FROM crosswalk_best b
    JOIN (
        SELECT ncessch
        FROM sandbox.ref_school_identity_crosswalk_review
        GROUP BY ncessch
        HAVING COUNT(DISTINCT (school_name_normalized, system_name_normalized)) = 1
    ) u
      ON u.ncessch = b.ncessch
    WHERE b.rn = 1
),
ranked AS (
    SELECT d.*, ROW_NUMBER() OVER (
        PARTITION BY d.year, d.district_name, d.school_name
        ORDER BY d._ingested_at DESC NULLS LAST, d._source_file DESC NULLS LAST
    ) AS rn
    FROM sandbox.dim_school_info_draft d
    WHERE d.year IS NOT NULL
      AND (d.year ~ '^[0-9]{4}$' OR d.year ~ '^[0-9]{4}-[0-9]{4}$')
      AND d.district_name IS NOT NULL
      AND d.school_name IS NOT NULL
),
base AS (
    SELECT
        d.year,
        regexp_replace(trim(d.district_name), '[[:space:]]+', ' ', 'g') AS dist_name_clean,
        regexp_replace(trim(d.school_name), '[[:space:]]+', ' ', 'g') AS school_name_clean,
        CASE WHEN d.nces_id ~ '^[0-9]+$' THEN lpad(trim(d.nces_id), 12, '0')::char(12) END AS ncessch,
        CASE
            WHEN d.state_dist_id ~ '^AL-[0-9]+$' THEN split_part(d.state_dist_id, '-', 2)::int
            WHEN d.state_dist_id ~ '^[0-9]+$' THEN d.state_dist_id::int
            ELSE NULL
        END AS state_dist_id,
        CASE
            WHEN d.state_school_id ~ '^AL-[0-9]+-[0-9]+$' THEN split_part(d.state_school_id, '-', 3)::int
            WHEN d.state_school_id ~ '^[0-9]+$' THEN d.state_school_id::int
            ELSE NULL
        END AS state_school_id,
        CASE WHEN d.nces_admin_id ~ '^[0-9]+$' THEN d.nces_admin_id::bigint END AS nces_admin_id,
        CASE WHEN d.nces_geo_id ~ '^[0-9]+$' THEN d.nces_geo_id::bigint END AS nces_geo_id,
        CASE WHEN d.census_id ~ '^[0-9]+$' THEN d.census_id::bigint END AS census_id,
        CASE WHEN d.nces_id ~ '^[0-9]+$' THEN d.nces_id::bigint END AS nces_id,
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
        END AS locale_code,
        CASE
            WHEN lower(coalesce(d.nces_charter, '')) IN ('yes', 'y', 'true', 't', '1', '1-yes') THEN TRUE
            WHEN lower(coalesce(d.nces_charter, '')) IN ('no', 'n', 'false', 'f', '0', '2-no') THEN FALSE
            ELSE NULL
        END AS nces_charter,
        CASE
            WHEN lower(coalesce(d.nces_magnet, '')) IN ('yes', 'y', 'true', 't', '1', '1-yes') THEN TRUE
            WHEN lower(coalesce(d.nces_magnet, '')) IN ('no', 'n', 'false', 'f', '0', '2-no') THEN FALSE
            ELSE NULL
        END AS nces_magnet,
        NULLIF(d.nces_address, '') AS nces_address,
        NULLIF(d.nces_city, '') AS nces_city,
        NULLIF(d.nces_zip, '') AS nces_zip,
        d.nces_locale AS source_nces_locale,
        d.state_dist_id AS source_state_dist_id,
        d.state_school_id AS source_state_school_id,
        d._source_file,
        d._ingested_at
    FROM ranked d
    WHERE d.rn = 1
),
resolved AS (
    SELECT
        'AL'::char(2) AS state_code,
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
        coalesce(x.dist_name_xw, b.dist_name_clean) AS dist_name,
        coalesce(x.school_name_xw, b.school_name_clean) AS school_name,
        b.state_dist_id,
        b.state_school_id,
        b.nces_admin_id,
        b.nces_geo_id,
        b.census_id,
        b.nces_id,
        coalesce(loc.nces_locale_key, u.nces_locale_key) AS nces_locale_key,
        coalesce(loc.locale_group, u.locale_group) AS nces_locale_type,
        coalesce(loc.locale_subtype, u.locale_subtype) AS nces_locale_subtype,
        b.nces_charter,
        b.nces_magnet,
        b.nces_address,
        b.nces_city,
        b.nces_zip,
        b.source_nces_locale,
        b.source_state_dist_id,
        b.source_state_school_id,
        b._source_file,
        b._ingested_at,
        0 AS source_priority
    FROM base b
    LEFT JOIN crosswalk_unique x
      ON x.ncessch = b.ncessch
    LEFT JOIN ref.nces_locale_canonical loc
      ON loc.locale_code = b.locale_code
    CROSS JOIN unk u
),
missing_school_year AS (
    SELECT DISTINCT
        'AL'::char(2) AS state_code,
        concat(t.year::text, '-', (t.year + 1)::text) AS school_year_label,
        t.year::smallint AS school_year_start,
        (t.year + 1)::smallint AS school_year_end,
        regexp_replace(trim(t.system), '[[:space:]]+', ' ', 'g') AS dist_name,
        regexp_replace(trim(t.school), '[[:space:]]+', ' ', 'g') AS school_name,
        u.nces_locale_key,
        u.locale_group AS nces_locale_type,
        u.locale_subtype AS nces_locale_subtype
    FROM sandbox.impute_teacher_demographics t
    CROSS JOIN unk u
    WHERE NOT EXISTS (
        SELECT 1
        FROM resolved r
        WHERE r.school_year_start = t.year::smallint
          AND lower(regexp_replace(trim(r.dist_name), '[[:space:]]+', ' ', 'g'))
              = lower(regexp_replace(trim(t.system), '[[:space:]]+', ' ', 'g'))
          AND lower(regexp_replace(trim(r.school_name), '[[:space:]]+', ' ', 'g'))
              = lower(regexp_replace(trim(t.school), '[[:space:]]+', ' ', 'g'))
    )
),
combined AS (
    SELECT * FROM resolved
    UNION ALL
    SELECT
        m.state_code,
        m.school_year_label,
        m.school_year_start,
        m.school_year_end,
        m.dist_name,
        m.school_name,
        NULL::int,
        NULL::int,
        NULL::bigint,
        NULL::bigint,
        NULL::bigint,
        NULL::bigint,
        m.nces_locale_key,
        m.nces_locale_type,
        m.nces_locale_subtype,
        NULL::boolean,
        NULL::boolean,
        NULL::text,
        NULL::varchar(120),
        NULL::varchar(15),
        NULL::text,
        NULL::text,
        NULL::text,
        'impute_teacher_demographics'::text,
        now()::timestamp,
        1
    FROM missing_school_year m
),
deduped AS (
    SELECT *
    FROM (
        SELECT
            c.*,
            lower(regexp_replace(trim(c.dist_name), '[[:space:]]+', ' ', 'g')) AS dist_name_norm,
            lower(regexp_replace(trim(c.school_name), '[[:space:]]+', ' ', 'g')) AS school_name_norm,
            ROW_NUMBER() OVER (
                PARTITION BY c.school_year_start,
                    lower(regexp_replace(trim(c.dist_name), '[[:space:]]+', ' ', 'g')),
                    lower(regexp_replace(trim(c.school_name), '[[:space:]]+', ' ', 'g'))
                ORDER BY
                    c.source_priority,
                    CASE WHEN c.state_dist_id IS NOT NULL THEN 0 ELSE 1 END,
                    CASE WHEN c.state_school_id IS NOT NULL THEN 0 ELSE 1 END,
                    CASE WHEN c.nces_id IS NOT NULL THEN 0 ELSE 1 END,
                    c._ingested_at DESC NULLS LAST,
                    c._source_file
            ) AS rn
        FROM combined c
    ) x
    WHERE x.rn = 1
)
SELECT
    d.state_code,
    d.school_year_label,
    d.school_year_start,
    d.school_year_end,
    regexp_replace(trim(d.dist_name), '[[:space:]]+', ' ', 'g') AS dist_name,
    regexp_replace(trim(d.school_name), '[[:space:]]+', ' ', 'g') AS school_name,
    d.dist_name_norm,
    d.school_name_norm,
    CASE
        WHEN d.dist_name_norm = d.school_name_norm
         AND d.dist_name_norm LIKE '%state department of education%' THEN 'STATE'
        WHEN d.dist_name_norm = d.school_name_norm THEN 'DISTRICT'
        ELSE 'SCHOOL'
    END AS row_type,
    d.state_dist_id,
    d.state_school_id,
    d.nces_admin_id,
    d.nces_geo_id,
    d.census_id,
    d.nces_id,
    d.nces_locale_key,
    d.nces_locale_type,
    d.nces_locale_subtype,
    d.nces_charter,
    d.nces_magnet,
    d.nces_address,
    d.nces_city,
    d.nces_zip,
    d.source_nces_locale,
    d.source_state_dist_id,
    d.source_state_school_id,
    d._source_file,
    d._ingested_at
FROM deduped d;

INSERT INTO sandbox.dim_state_review (state_key, state_code, state_name)
VALUES (1, 'AL', 'Alabama');

CREATE TEMP TABLE _district_seed AS
SELECT *
FROM (
    SELECT
        p.state_code,
        p.dist_name_norm,
        p.dist_name,
        p.state_dist_id,
        p.nces_admin_id,
        p.source_state_dist_id,
        ROW_NUMBER() OVER (
            PARTITION BY p.state_code, p.dist_name_norm
            ORDER BY
                CASE WHEN p.state_dist_id IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN p.nces_admin_id IS NOT NULL THEN 0 ELSE 1 END,
                p.dist_name
        ) AS rn
    FROM _school_rows_prepared p
    WHERE p.row_type IN ('DISTRICT', 'SCHOOL')
      AND p.dist_name_norm NOT LIKE '%state department of education%'
) x
WHERE rn = 1;

INSERT INTO sandbox.dim_district_review (
    district_key,
    state_key,
    state_code,
    district_name,
    district_name_norm,
    state_dist_id,
    nces_admin_id,
    source_state_dist_id
)
SELECT
    DENSE_RANK() OVER (ORDER BY d.state_code, d.dist_name)::bigint AS district_key,
    1,
    d.state_code,
    d.dist_name,
    d.dist_name_norm,
    d.state_dist_id,
    d.nces_admin_id,
    d.source_state_dist_id
FROM _district_seed d;

CREATE TEMP TABLE _school_seed AS
SELECT *
FROM (
    SELECT
        p.state_code,
        p.dist_name_norm,
        p.school_name_norm,
        p.school_name,
        p.state_school_id,
        p.nces_geo_id,
        p.census_id,
        p.nces_id,
        p.nces_charter,
        p.nces_magnet,
        p.nces_address,
        p.nces_city,
        p.nces_zip,
        p.source_state_school_id,
        ROW_NUMBER() OVER (
            PARTITION BY p.state_code, p.dist_name_norm, p.school_name_norm
            ORDER BY
                CASE WHEN p.state_school_id IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN p.nces_id IS NOT NULL THEN 0 ELSE 1 END,
                p.school_name
        ) AS rn
    FROM _school_rows_prepared p
    WHERE p.row_type = 'SCHOOL'
) x
WHERE rn = 1;

INSERT INTO sandbox.dim_school_review (
    school_key,
    district_key,
    state_code,
    school_name,
    school_name_norm,
    state_school_id,
    nces_geo_id,
    census_id,
    nces_id,
    nces_charter,
    nces_magnet,
    nces_address,
    nces_city,
    nces_zip,
    source_state_school_id
)
SELECT
    DENSE_RANK() OVER (ORDER BY d.district_key, s.school_name)::bigint AS school_key,
    d.district_key,
    s.state_code,
    s.school_name,
    s.school_name_norm,
    s.state_school_id,
    s.nces_geo_id,
    s.census_id,
    s.nces_id,
    s.nces_charter,
    s.nces_magnet,
    s.nces_address,
    s.nces_city,
    s.nces_zip,
    s.source_state_school_id
FROM _school_seed s
JOIN sandbox.dim_district_review d
  ON d.state_code = s.state_code
 AND d.district_name_norm = s.dist_name_norm;

INSERT INTO sandbox.bridge_school_year_review (
    school_key,
    school_year_label,
    school_year_start,
    school_year_end,
    nces_locale_key,
    nces_locale_type,
    nces_locale_subtype,
    source_nces_locale,
    _source_file,
    _ingested_at
)
SELECT
    s.school_key,
    p.school_year_label,
    p.school_year_start,
    p.school_year_end,
    p.nces_locale_key,
    p.nces_locale_type,
    p.nces_locale_subtype,
    p.source_nces_locale,
    p._source_file,
    p._ingested_at
FROM _school_rows_prepared p
JOIN sandbox.dim_district_review d
  ON d.state_code = p.state_code
 AND d.district_name_norm = p.dist_name_norm
JOIN sandbox.dim_school_review s
  ON s.district_key = d.district_key
 AND s.school_name_norm = p.school_name_norm
WHERE p.row_type = 'SCHOOL'
ON CONFLICT (school_key, school_year_start) DO UPDATE SET
    school_year_label   = EXCLUDED.school_year_label,
    school_year_end     = EXCLUDED.school_year_end,
    nces_locale_key     = EXCLUDED.nces_locale_key,
    nces_locale_type    = EXCLUDED.nces_locale_type,
    nces_locale_subtype = EXCLUDED.nces_locale_subtype,
    source_nces_locale  = EXCLUDED.source_nces_locale,
    _source_file        = EXCLUDED._source_file,
    _ingested_at        = EXCLUDED._ingested_at,
    _updated_at         = now();

INSERT INTO sandbox.dim_school_info_review (
    school_key,
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
    sy.school_key,
    sy.school_year_label,
    sy.school_year_start,
    sy.school_year_end,
    sc.state_code,
    d.state_dist_id,
    sc.state_school_id,
    d.nces_admin_id,
    sc.nces_geo_id,
    sc.census_id,
    sc.nces_id,
    d.district_name,
    sc.school_name,
    sy.nces_locale_key,
    sy.nces_locale_type,
    sy.nces_locale_subtype,
    sc.nces_charter,
    sc.nces_magnet,
    sc.nces_address,
    sc.nces_city,
    sc.nces_zip,
    sy.source_nces_locale,
    d.source_state_dist_id,
    sc.source_state_school_id,
    sy._source_file,
    sy._ingested_at
FROM sandbox.bridge_school_year_review sy
JOIN sandbox.dim_school_review sc ON sc.school_key = sy.school_key
JOIN sandbox.dim_district_review d ON d.district_key = sc.district_key;

CREATE UNIQUE INDEX uq_dim_school_review_norm
  ON sandbox.dim_school_info_review (
    school_year_label,
    lower(regexp_replace(trim(dist_name), '[[:space:]]+', ' ', 'g')),
    lower(regexp_replace(trim(school_name), '[[:space:]]+', ' ', 'g'))
  );

CREATE INDEX idx_school_info_review_year_name
  ON sandbox.dim_school_info_review (school_year_start, dist_name, school_name);
CREATE INDEX idx_school_info_review_state_ids
  ON sandbox.dim_school_info_review (state_code, state_dist_id, state_school_id);
CREATE INDEX idx_school_info_review_locale
  ON sandbox.dim_school_info_review (nces_locale_key);
CREATE INDEX idx_dim_district_review_name
  ON sandbox.dim_district_review (state_code, district_name_norm);
CREATE INDEX idx_dim_school_review_name
  ON sandbox.dim_school_review (district_key, school_name_norm);
CREATE INDEX idx_bridge_school_year_review_year
  ON sandbox.bridge_school_year_review (school_year_start);
