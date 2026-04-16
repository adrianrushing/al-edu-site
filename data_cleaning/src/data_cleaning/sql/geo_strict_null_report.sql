-- Report strict-null coverage for school-to-county mapping.
-- Run after sandbox_geo_review_models.sql (sandbox) or core_load_geo_to_core.sql (core).

-- Sandbox summary
SELECT
    coalesce(strict_null_reason, 'MATCHED') AS mapping_status,
    count(*) AS row_count
FROM sandbox.bridge_school_geo_county_review
GROUP BY coalesce(strict_null_reason, 'MATCHED')
ORDER BY row_count DESC;

-- Sandbox method summary
SELECT
    coalesce(match_method, 'NO_METHOD') AS match_method,
    count(*) AS row_count
FROM sandbox.bridge_school_geo_county_review
GROUP BY coalesce(match_method, 'NO_METHOD')
ORDER BY row_count DESC;

-- Sandbox by year
SELECT
    school_year_start,
    coalesce(strict_null_reason, 'MATCHED') AS mapping_status,
    count(*) AS row_count
FROM sandbox.bridge_school_geo_county_review
GROUP BY school_year_start, coalesce(strict_null_reason, 'MATCHED')
ORDER BY school_year_start, row_count DESC;

-- Core summary (if loaded)
SELECT
    coalesce(strict_null_reason, 'MATCHED') AS mapping_status,
    count(*) AS row_count
FROM core.bridge_school_geo_county
GROUP BY coalesce(strict_null_reason, 'MATCHED')
ORDER BY row_count DESC;
