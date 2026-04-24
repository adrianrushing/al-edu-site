from __future__ import annotations

import argparse
import os
import re
from datetime import UTC, datetime

import polars as pl
import psycopg

DEFAULT_DB_URI = "postgresql://localhost:5433/eflt"
DEFAULT_SOURCE_TABLE = "staging.stg_student_demographics"
DEFAULT_TARGET_TABLE = "sandbox.impute_student_demographics_long"

TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")

SUPPRESSION_TOKENS = {
    "",
    "*",
    "**",
    "--",
    "~",
    "SUPP",
    "SUPPRESSED",
    "NA",
    "N/A",
    "NRD",
    "NULL",
}

KEY_COLS = [
    "year",
    "system",
    "school",
    "grade",
    "gender",
    "ethnicity",
    "sub_population",
]

RACE_COLS = [
    "asian",
    "black_or_african_american",
    "american_indian_alaska_native",
    "native_hawaiian_pacific_islander",
    "white",
    "two_or_more_races",
]

COUNT_COLS = ["total_student_count", *RACE_COLS]

RACE_MAP: list[tuple[str, str]] = [
    ("all_races", "total_student_count"),
    ("asian", "asian"),
    ("black_or_african_american", "black_or_african_american"),
    ("american_indian_alaska_native", "american_indian_alaska_native"),
    ("native_hawaiian_pacific_islander", "native_hawaiian_pacific_islander"),
    ("white", "white"),
    ("two_or_more_races", "two_or_more_races"),
]


def validated_table_name(name: str) -> str:
    if not TABLE_NAME_RE.match(name):
        raise ValueError(f"Invalid table name: {name}")
    return name


def normalize_text_expr(col_name: str) -> pl.Expr:
    return (
        pl.col(col_name)
        .cast(pl.String, strict=False)
        .str.strip_chars()
        .str.replace_all(r"[[:space:]]+", " ")
    )


def parse_year_expr() -> pl.Expr:
    year_raw = normalize_text_expr("year")
    return (
        pl.when(year_raw.str.contains(r"^\d{4}-\d{4}$"))
        .then(year_raw.str.slice(0, 4).cast(pl.Int32, strict=False))
        .when(year_raw.str.contains(r"^\d{4}$"))
        .then(year_raw.cast(pl.Int32, strict=False))
        .otherwise(None)
    )


def parse_count_expr(col_name: str) -> pl.Expr:
    raw = pl.col(col_name).cast(pl.String, strict=False).str.strip_chars()
    upper = raw.str.to_uppercase()
    cleaned = raw.str.replace_all(r"[^0-9\.-]", "")
    return (
        pl.when(raw.is_null() | upper.is_in(list(SUPPRESSION_TOKENS)))
        .then(None)
        .otherwise(cleaned.cast(pl.Int64, strict=False))
    )


def null_cell_count(df: pl.DataFrame) -> int:
    total = df.select(
        sum(pl.col(col).is_null().cast(pl.Int64).sum() for col in COUNT_COLS)
    ).item()
    return int(total or 0)


def fill_once(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    before = null_cell_count(df)

    race_sum = pl.sum_horizontal([pl.col(col) for col in RACE_COLS])
    all_races_present = pl.all_horizontal([pl.col(col).is_not_null() for col in RACE_COLS])

    out = df.with_columns(
        pl.when(pl.col("total_student_count").is_null() & all_races_present)
        .then(race_sum)
        .otherwise(pl.col("total_student_count"))
        .alias("total_student_count")
    )

    race_updates: list[pl.Expr] = []
    for race in RACE_COLS:
        others = [col for col in RACE_COLS if col != race]
        others_sum = pl.sum_horizontal([pl.col(col) for col in others])
        others_present = pl.all_horizontal([pl.col(col).is_not_null() for col in others])
        candidate = pl.col("total_student_count") - others_sum

        race_updates.append(
            pl.when(
                pl.col(race).is_null()
                & pl.col("total_student_count").is_not_null()
                & others_present
                & candidate.is_not_null()
                & (candidate >= 0)
                & (candidate <= 9)
            )
            .then(candidate)
            .otherwise(pl.col(race))
            .alias(race)
        )

    out = out.with_columns(race_updates)
    after = null_cell_count(out)
    return out, before - after


def run_imputation(df: pl.DataFrame, max_iter: int) -> tuple[pl.DataFrame, int]:
    out = df
    total_filled = 0

    for _ in range(max_iter):
        out, filled = fill_once(out)
        total_filled += filled
        if filled == 0:
            break

    return out, total_filled


def fetch_years(db_uri: str, source_table: str) -> list[int]:
    table = validated_table_name(source_table)
    query = f"""
        SELECT DISTINCT
            CASE
                WHEN year ~ '^[0-9]{{4}}-[0-9]{{4}}$' THEN split_part(year, '-', 1)::int
                WHEN year ~ '^[0-9]{{4}}$' THEN year::int
                ELSE NULL
            END AS year_start
        FROM {table}
        WHERE year IS NOT NULL
        ORDER BY year_start
    """
    with psycopg.connect(db_uri) as conn:
        years_df = pl.read_database(query=query, connection=conn)

    return [
        int(year)
        for year in years_df.get_column("year_start").to_list()
        if year is not None
    ]


def load_source_for_year(db_uri: str, source_table: str, year: int) -> pl.DataFrame:
    table = validated_table_name(source_table)
    query = f"""
        SELECT
            year,
            system,
            school,
            grade,
            gender,
            ethnicity,
            sub_population,
            total_student_count,
            asian,
            black_or_african_american,
            american_indian_alaska_native,
            native_hawaiian_pacific_islander,
            white,
            two_or_more_races,
            _ingested_at
        FROM {table}
        WHERE
            (
                year ~ '^[0-9]{{4}}$'
                AND year::int = {year}
            )
            OR (
                year ~ '^[0-9]{{4}}-[0-9]{{4}}$'
                AND split_part(year, '-', 1)::int = {year}
            )
    """
    with psycopg.connect(db_uri) as conn:
        return pl.read_database(query=query, connection=conn)


def prepare_source(raw: pl.DataFrame) -> pl.DataFrame:
    prepared = raw.with_columns(
        [
            parse_year_expr().alias("year"),
            normalize_text_expr("system").alias("system"),
            normalize_text_expr("school").alias("school"),
            normalize_text_expr("grade").alias("grade"),
            normalize_text_expr("gender").alias("gender"),
            normalize_text_expr("ethnicity").alias("ethnicity"),
            normalize_text_expr("sub_population").alias("sub_population"),
            *[parse_count_expr(col).alias(col) for col in COUNT_COLS],
        ]
    ).filter(
        pl.col("year").is_not_null()
        & pl.col("system").is_not_null()
        & (pl.col("system") != "")
        & pl.col("school").is_not_null()
        & (pl.col("school") != "")
    )

    deduped = (
        prepared.sort(by=["_ingested_at"], descending=[True], nulls_last=True)
        .unique(subset=KEY_COLS, keep="first", maintain_order=True)
        .drop("_ingested_at")
    )
    return deduped


def to_long(df: pl.DataFrame) -> pl.DataFrame:
    frames: list[pl.DataFrame] = []
    for race_name, source_col in RACE_MAP:
        frames.append(
            df.select(
                [
                    "year",
                    "system",
                    "school",
                    "grade",
                    "gender",
                    "ethnicity",
                    "sub_population",
                    pl.lit(race_name).alias("race"),
                    pl.col(source_col).alias("count"),
                ]
            )
        )

    long_df = pl.concat(frames, how="vertical")
    now_ts = datetime.now(UTC)
    return long_df.with_columns(
        [
            pl.lit(now_ts).alias("_created_at"),
            pl.lit(now_ts).alias("_updated_at"),
        ]
    )


def write_output(df: pl.DataFrame, db_uri: str, target_table: str, mode: str) -> None:
    table = validated_table_name(target_table)
    df.write_database(
        table_name=table,
        connection=db_uri,
        if_table_exists=mode,
        engine="adbc",
    )


def run(db_uri: str, source_table: str, target_table: str, max_iter: int) -> None:
    years = fetch_years(db_uri, source_table)
    if not years:
        raise RuntimeError(f"No parseable years found in {source_table}")

    total_rows = 0
    total_filled = 0
    first_write = True

    for year in years:
        raw = load_source_for_year(db_uri, source_table, year)
        if raw.is_empty():
            continue

        prepared = prepare_source(raw)
        imputed, filled_cells = run_imputation(prepared, max_iter=max_iter)
        long_df = to_long(imputed)
        write_mode = "replace" if first_write else "append"
        write_output(long_df, db_uri=db_uri, target_table=target_table, mode=write_mode)

        first_write = False
        total_rows += long_df.height
        total_filled += filled_cells

        print(
            f"year={year} rows_written={long_df.height} imputed_cells={filled_cells} mode={write_mode}"
        )

    print(f"rows_written={total_rows}")
    print(f"imputed_cells={total_filled}")
    print(f"year_min={min(years)}")
    print(f"year_max={max(years)}")
    print(f"target_table={target_table}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight student demographics imputation to sandbox long table."
    )
    parser.add_argument(
        "--db-uri",
        default=os.getenv("DATABASE_URL") or os.getenv("DB_URI") or DEFAULT_DB_URI,
    )
    parser.add_argument("--source-table", default=DEFAULT_SOURCE_TABLE)
    parser.add_argument("--target-table", default=DEFAULT_TARGET_TABLE)
    parser.add_argument("--max-iter", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        db_uri=args.db_uri,
        source_table=args.source_table,
        target_table=args.target_table,
        max_iter=args.max_iter,
    )
