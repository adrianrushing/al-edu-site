from __future__ import annotations

import argparse
import os

import polars as pl
import psycopg

from data_cleaning.modeling.mlr import train_achievement_model


MODEL_QUERY = """
WITH base AS (
  SELECT school_key, year, county_fips
  FROM core.vw_school_year_geo_context
  WHERE year >= %s
),
student AS (
  SELECT
    school_key,
    year,
    student_diversity_index,
    student_prevalence_1st_pct,
    student_prevalence_2nd_pct,
    student_prevalence_3rd_pct,
    student_diffusion_score_pct
  FROM core.mv_student_census_features
),
staff AS (
  SELECT
    school_key,
    year,
    teacher_diversity_index,
    teacher_diversity_chance_pct,
    teacher_prevalence_1st_pct,
    teacher_prevalence_2nd_pct,
    teacher_prevalence_3rd_pct,
    teacher_diffusion_score_pct,
    teacher_support_staff_pct,
    total_staff_count
  FROM core.mv_staff_census_features
),
teacher_exp AS (
  SELECT
    school_key,
    year,
    principal_exp_pct,
    principal_inexp_pct,
    teacher_exp_pct,
    teacher_inexp_pct,
    leader_exp_pct,
    leader_inexp_pct
  FROM core.mv_teacher_experience_pivot
),
teacher_eff AS (
  SELECT
    school_key,
    year,
    effectiveness_score AS teacher_effectiveness_score
  FROM core.fact_teacher_effectiveness
),
school_outcomes AS (
  SELECT
    school_key,
    year,
    ach_all,
    grw_all,
    abs_all,
    coi,
    coi_ed,
    coi_he,
    coi_st,
    ppe
  FROM core.fact_school_outcomes_wide
),
area_opp AS (
  SELECT
    county_fips,
    year,
    MAX(opportunity_score_avg) FILTER (WHERE metric_code='COI' AND norm_scope='stt') AS county_coi_score_stt,
    MAX(opportunity_zscore_avg) FILTER (WHERE metric_code='COI' AND norm_scope='stt') AS county_coi_z_stt,
    MAX(opportunity_score_avg) FILTER (WHERE metric_code='COI' AND norm_scope='met') AS county_coi_score_met,
    MAX(opportunity_zscore_avg) FILTER (WHERE metric_code='COI' AND norm_scope='met') AS county_coi_z_met
  FROM core.fact_geo_opportunity_county
  GROUP BY county_fips, year
)
SELECT
  b.school_key,
  b.year,
  st.student_diversity_index,
  st.student_prevalence_1st_pct,
  st.student_prevalence_2nd_pct,
  st.student_prevalence_3rd_pct,
  st.student_diffusion_score_pct,
  sf.teacher_diversity_index,
  sf.teacher_diversity_chance_pct,
  sf.teacher_prevalence_1st_pct,
  sf.teacher_prevalence_2nd_pct,
  sf.teacher_prevalence_3rd_pct,
  sf.teacher_diffusion_score_pct,
  sf.teacher_support_staff_pct,
  sf.total_staff_count,
  te.principal_exp_pct,
  te.principal_inexp_pct,
  te.teacher_exp_pct,
  te.teacher_inexp_pct,
  te.leader_exp_pct,
  te.leader_inexp_pct,
  tf.teacher_effectiveness_score,
  so.ach_all,
  so.grw_all,
  so.abs_all,
  so.coi,
  so.coi_ed,
  so.coi_he,
  so.coi_st,
  so.ppe,
  ao.county_coi_score_stt,
  ao.county_coi_z_stt,
  ao.county_coi_score_met,
  ao.county_coi_z_met
FROM base b
LEFT JOIN student st USING (school_key, year)
LEFT JOIN staff sf USING (school_key, year)
LEFT JOIN teacher_exp te USING (school_key, year)
LEFT JOIN teacher_eff tf USING (school_key, year)
LEFT JOIN school_outcomes so USING (school_key, year)
LEFT JOIN area_opp ao ON ao.county_fips = b.county_fips AND ao.year = b.year
"""


def _query_to_polars(
    database_url: str, query: str, params: tuple[int, ...]
) -> pl.DataFrame:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    return pl.from_dicts([dict(zip(columns, row)) for row in rows])


def _prepare(df: pl.DataFrame) -> pl.DataFrame:
    numeric_cols = [
        "student_diversity_index",
        "teacher_diversity_index",
        "teacher_exp_pct",
        "teacher_inexp_pct",
        "leader_exp_pct",
        "leader_inexp_pct",
        "principal_exp_pct",
        "principal_inexp_pct",
        "student_prevalence_1st_pct",
        "student_prevalence_2nd_pct",
        "student_prevalence_3rd_pct",
        "student_diffusion_score_pct",
        "teacher_prevalence_1st_pct",
        "teacher_prevalence_2nd_pct",
        "teacher_prevalence_3rd_pct",
        "teacher_diffusion_score_pct",
        "teacher_support_staff_pct",
        "total_staff_count",
        "grw_all",
        "abs_all",
        "ach_all",
        "coi",
        "coi_ed",
        "coi_he",
        "coi_st",
        "ppe",
        "county_coi_score_stt",
        "county_coi_z_stt",
        "county_coi_score_met",
        "county_coi_z_met",
    ]
    clean = df.with_columns(
        pl.when(
            pl.col("teacher_effectiveness_score").is_in(["Missing Data", "No Data", ""])
        )
        .then(None)
        .otherwise(pl.col("teacher_effectiveness_score"))
        .alias("teacher_effectiveness_score")
    )
    clean = clean.with_columns(
        [
            pl.col(c).cast(pl.Float64, strict=False).alias(c)
            for c in numeric_cols + ["teacher_effectiveness_score"]
            if c in clean.columns
        ]
    )
    return clean


def run_model(
    database_url: str,
    min_year: int = 2021,
    cv_splits: int = 5,
):
    achievement_df = _prepare(_query_to_polars(database_url, MODEL_QUERY, (min_year,)))

    excluded_features = {
        "school_key",
    }

    features = [
        col
        for col in achievement_df.columns
        if col != "ach_all"
        and col not in excluded_features
        and achievement_df[col].null_count() < achievement_df.height
    ]

    ach_result = train_achievement_model(
        achievement_df,
        feature_cols=features,
        cv_splits=cv_splits,
    )
    return ach_result


def _print_result(result) -> None:
    print(f"\n=== {result.target_name.upper()} MODEL ===")
    print("Selected features:", ", ".join(result.selected_features) or "(none)")
    print("CV metrics:")
    for metric, vals in result.cv_metrics.items():
        print(f"  {metric.upper():<5} mean={vals['mean']:.4f} std={vals['std']:.4f}")
    print("Feature selection frequency:")
    for feature, freq in sorted(
        result.feature_selection_freq.items(), key=lambda item: item[1], reverse=True
    ):
        print(f"  {feature:<28} {freq:.2f}")
    print("\nOLS summary:")
    print(result.statsmodels_summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run standalone achievement model.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--min-year", type=int, default=2021)
    parser.add_argument("--cv-splits", type=int, default=5)
    args = parser.parse_args()

    if not args.database_url:
        raise RuntimeError("DATABASE_URL is required (env var or --database-url)")

    ach_result = run_model(
        database_url=args.database_url,
        min_year=args.min_year,
        cv_splits=args.cv_splits,
    )
    _print_result(ach_result)


if __name__ == "__main__":
    main()
