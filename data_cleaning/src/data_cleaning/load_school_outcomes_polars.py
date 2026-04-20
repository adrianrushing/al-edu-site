from __future__ import annotations

import os
from pathlib import Path

import polars as pl


DEFAULT_DB_URI = "postgresql://localhost:5433/eflt"

RAW_TO_STAGING = {
    "Year": "year",
    "System": "system",
    "School": "school",
    "Enrollment": "enrollment",
    "AchAll": "achall",
    "GrwAll": "grwall",
    "AbsAll": "absall",
    "AchECD": "achecd",
    "GrwECD": "grwecd",
    "AbsECD": "absecd",
    "AchESL": "achesl",
    "GrwESL": "grwesl",
    "AbsESL": "absesl",
    "AchAsian": "achasian",
    "GrwAsian": "grwasian",
    "AbsAsian": "absasian",
    "AchBlack": "achblack",
    "GrwBlack": "grwblack",
    "AbsBlack": "absblack",
    "AchHsp": "achhsp",
    "GrwHsp": "grwhsp",
    "AbsHsp": "abshsp",
    "AchWhite": "achwhite",
    "GrwWhite": "grwwhite",
    "AbsWhite": "abswhite",
    "AchOther": "achother",
    "GrwOther": "grwother",
    "AbsOther": "absother",
    "DISTRICT": "district",
}


def db_uri() -> str:
    return os.getenv("DATABASE_URL") or os.getenv("DB_URI") or DEFAULT_DB_URI


def normalize_text_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .cast(pl.String)
        .str.strip_chars()
        .str.replace_all(r"[[:space:]]+", " ")
    )


def parse_int_expr(col: str) -> pl.Expr:
    cleaned = pl.col(col).cast(pl.String).str.strip_chars().str.replace_all(",", "")
    return (
        pl.when(cleaned.str.contains(r"^[-]?[0-9]+(\.[0-9]+)?$"))
        .then(
            cleaned.cast(pl.Float64, strict=False).round(0).cast(pl.Int64, strict=False)
        )
        .otherwise(None)
    )


def parse_float_expr(col: str) -> pl.Expr:
    cleaned = pl.col(col).cast(pl.String).str.strip_chars().str.replace_all(",", "")
    return (
        pl.when(cleaned.str.contains(r"^[-]?[0-9]+(\.[0-9]+)?$"))
        .then(cleaned.cast(pl.Float64, strict=False))
        .otherwise(None)
    )


def load_staging(source_path: Path) -> pl.DataFrame:
    raw = pl.read_csv(source_path, infer_schema_length=0)

    stg = (
        raw.select(list(RAW_TO_STAGING.keys()))
        .rename(RAW_TO_STAGING)
        .with_columns(
            [normalize_text_expr(c).alias(c) for c in RAW_TO_STAGING.values()]
        )
        .with_columns(
            [
                pl.when(pl.col(c).is_null() | (pl.col(c) == ""))
                .then(None)
                .otherwise(pl.col(c))
                .alias(c)
                for c in RAW_TO_STAGING.values()
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("district").is_null())
                .then(pl.col("system"))
                .otherwise(pl.col("district"))
                .alias("district")
            ]
        )
    )

    stg.write_database(
        table_name="staging.stg_school_outcomes",
        connection=db_uri(),
        if_table_exists="replace",
        engine="adbc",
    )
    return stg


def build_review(stg: pl.DataFrame) -> pl.DataFrame:
    typed = stg.with_columns(
        [
            parse_int_expr("year").cast(pl.Int32).alias("year"),
            normalize_text_expr("system").alias("dist_name"),
            normalize_text_expr("school").alias("school_name"),
            parse_int_expr("enrollment").alias("enrollment"),
            parse_float_expr("achall").alias("ach_all"),
            parse_float_expr("grwall").alias("grw_all"),
            parse_float_expr("absall").alias("abs_all"),
            parse_float_expr("achecd").alias("ach_ecd"),
            parse_float_expr("grwecd").alias("grw_ecd"),
            parse_float_expr("absecd").alias("abs_ecd"),
            parse_float_expr("achesl").alias("ach_esl"),
            parse_float_expr("grwesl").alias("grw_esl"),
            parse_float_expr("absesl").alias("abs_esl"),
            parse_float_expr("achasian").alias("ach_asian"),
            parse_float_expr("grwasian").alias("grw_asian"),
            parse_float_expr("absasian").alias("abs_asian"),
            parse_float_expr("achblack").alias("ach_black"),
            parse_float_expr("grwblack").alias("grw_black"),
            parse_float_expr("absblack").alias("abs_black"),
            parse_float_expr("achhsp").alias("ach_hsp"),
            parse_float_expr("grwhsp").alias("grw_hsp"),
            parse_float_expr("abshsp").alias("abs_hsp"),
            parse_float_expr("achwhite").alias("ach_white"),
            parse_float_expr("grwwhite").alias("grw_white"),
            parse_float_expr("abswhite").alias("abs_white"),
            parse_float_expr("achother").alias("ach_other"),
            parse_float_expr("grwother").alias("grw_other"),
            parse_float_expr("absother").alias("abs_other"),
        ]
    ).filter(
        pl.col("year").is_not_null()
        & pl.col("dist_name").is_not_null()
        & pl.col("school_name").is_not_null()
        & (pl.col("dist_name") != "")
        & (pl.col("school_name") != "")
    )

    value_cols = ["enrollment"] + [
        "ach_all",
        "grw_all",
        "abs_all",
        "ach_ecd",
        "grw_ecd",
        "abs_ecd",
        "ach_esl",
        "grw_esl",
        "abs_esl",
        "ach_asian",
        "grw_asian",
        "abs_asian",
        "ach_black",
        "grw_black",
        "abs_black",
        "ach_hsp",
        "grw_hsp",
        "abs_hsp",
        "ach_white",
        "grw_white",
        "abs_white",
        "ach_other",
        "grw_other",
        "abs_other",
    ]

    scored = typed.with_columns(
        [
            normalize_text_expr("dist_name")
            .str.to_lowercase()
            .alias("_dist_name_norm"),
            normalize_text_expr("school_name")
            .str.to_lowercase()
            .alias("_school_name_norm"),
            pl.sum_horizontal(
                [pl.col(c).is_not_null().cast(pl.Int32) for c in value_cols]
            ).alias("_completeness"),
        ]
    )

    deduped = (
        scored.sort(
            by=["year", "_dist_name_norm", "_school_name_norm", "_completeness"],
            descending=[False, False, False, True],
            nulls_last=True,
        )
        .unique(
            subset=["year", "_dist_name_norm", "_school_name_norm"],
            keep="first",
            maintain_order=True,
        )
        .drop(["_dist_name_norm", "_school_name_norm", "_completeness"])
    )

    deduped.write_database(
        table_name="sandbox.fact_school_outcomes_demographic_review",
        connection=db_uri(),
        if_table_exists="replace",
        engine="adbc",
    )
    return deduped


def main() -> None:
    source_path = (
        Path(__file__).resolve().parents[3]
        / "flat_data"
        / "in"
        / "raw_data"
        / "al_sch24_v1.csv"
    )
    stg = load_staging(source_path)
    review = build_review(stg)

    print(f"wrote_staging_rows={stg.height}")
    print(f"wrote_review_rows={review.height}")


if __name__ == "__main__":
    main()
