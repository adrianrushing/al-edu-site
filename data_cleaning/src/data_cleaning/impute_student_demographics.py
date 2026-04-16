from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import polars as pl
import psycopg
from psycopg import sql


DB_URI = "postgresql://dev_user:dev_password@localhost:5433/eflt"
SOURCE_TABLE = "staging.stg_student_demographics"
TARGET_TABLE = "sandbox.impute_student_demographics_long"
DIAGNOSTICS_TABLE = "sandbox.impute_student_demographics_diagnostics"

KEY_COLS = [
    "year",
    "system",
    "school",
    "grade",
    "gender",
    "ethnicity",
    "sub_population",
]
COUNT_COLS = [
    "total_student_count",
    "asian",
    "black_or_african_american",
    "american_indian_alaska_native",
    "native_hawaiian_pacific_islander",
    "white",
    "two_or_more_races",
]
RACE_MAP = [
    ("all_races", "total_student_count"),
    ("asian", "asian"),
    ("black_or_african_american", "black_or_african_american"),
    ("american_indian_alaska_native", "american_indian_alaska_native"),
    ("native_hawaiian_pacific_islander", "native_hawaiian_pacific_islander"),
    ("white", "white"),
    ("two_or_more_races", "two_or_more_races"),
]
MASK_VALUES = ["*", "**", "--", "SUPP", "SUPPRESSED", ""]

STALE_TABLES = [
    "sandbox.fast_impute_2021",
    "sandbox.fast_impute_2021_race_long",
    "sandbox.fast_impute_student_demographics",
    "sandbox.fast_impute_student_demographics_long",
    "sandbox.stg_student_demographics_imputed",
    "sandbox.stg_student_demographics_imputation_audit",
]


@dataclass(frozen=True)
class Scope:
    year: str
    system: str | None = None
    district_only: bool = False


def normalize_count_expr(col_name: str) -> pl.Expr:
    value = pl.col(col_name).cast(pl.String, strict=False).str.strip_chars()
    return (
        pl.when(value.is_null() | value.is_in(MASK_VALUES))
        .then(None)
        .otherwise(value.cast(pl.Int64, strict=False))
    )


def count_null_cells(df: pl.DataFrame) -> int:
    return int(
        df.select(
            sum(pl.col(c).is_null().cast(pl.Int64).sum() for c in COUNT_COLS)
        ).item()
        or 0
    )


def count_null_long_cells(df: pl.DataFrame) -> int:
    return int(df.select(pl.col("count").is_null().cast(pl.Int64).sum()).item() or 0)


def within_suppressed_range(candidate: pl.Expr) -> pl.Expr:
    return (candidate >= 1) & (candidate <= 9)


def apply_vertical_rule(
    df: pl.DataFrame,
    metric: str,
    dim_col: str,
    group_keys: list[str],
    left_value: str,
    right_value: str,
    total_value: str,
) -> tuple[pl.DataFrame, int]:
    agg = df.group_by(group_keys).agg(
        [
            pl.col(metric).filter(pl.col(dim_col) == left_value).max().alias("_left"),
            pl.col(metric).filter(pl.col(dim_col) == right_value).max().alias("_right"),
            pl.col(metric).filter(pl.col(dim_col) == total_value).max().alias("_total"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col(metric).alias("_old_metric")]
    )

    candidate = (
        pl.when(
            (pl.col(dim_col) == left_value)
            & pl.col(metric).is_null()
            & pl.col("_total").is_not_null()
            & pl.col("_right").is_not_null()
        )
        .then(pl.col("_total") - pl.col("_right"))
        .when(
            (pl.col(dim_col) == right_value)
            & pl.col(metric).is_null()
            & pl.col("_total").is_not_null()
            & pl.col("_left").is_not_null()
        )
        .then(pl.col("_total") - pl.col("_left"))
        .when(
            (pl.col(dim_col) == total_value)
            & pl.col(metric).is_null()
            & pl.col("_left").is_not_null()
            & pl.col("_right").is_not_null()
        )
        .then(pl.col("_left") + pl.col("_right"))
        .otherwise(None)
    )

    out = (
        tmp.with_columns(
            [
                pl.when(
                    pl.col(metric).is_null()
                    & candidate.is_not_null()
                    & within_suppressed_range(candidate)
                )
                .then(candidate)
                .otherwise(pl.col(metric))
                .alias(metric)
            ]
        )
        .drop(["_left", "_right", "_total"])
        .with_columns(
            [
                (pl.col("_old_metric").is_null() & pl.col(metric).is_not_null())
                .cast(pl.Int8)
                .alias("_filled")
            ]
        )
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(["_old_metric", "_filled"]), filled


def apply_horizontal_race_rule(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    old_aliases = [pl.col(c).alias(f"_old_{c}") for c in COUNT_COLS]
    out = df.with_columns(old_aliases)

    race_children = [
        "asian",
        "black_or_african_american",
        "american_indian_alaska_native",
        "native_hawaiian_pacific_islander",
        "white",
        "two_or_more_races",
    ]
    child_sum = pl.col(race_children[0])
    for race_col in race_children[1:]:
        child_sum = child_sum + pl.col(race_col)

    updates: list[pl.Expr] = [
        pl.when(
            pl.col("total_student_count").is_null()
            & pl.all_horizontal([pl.col(c).is_not_null() for c in race_children])
            & within_suppressed_range(child_sum)
        )
        .then(child_sum)
        .otherwise(pl.col("total_student_count"))
        .alias("total_student_count")
    ]

    for metric in race_children:
        others = [c for c in race_children if c != metric]
        other_sum = sum(pl.col(c) for c in others)
        candidate = pl.col("total_student_count") - other_sum
        updates.append(
            pl.when(
                pl.col(metric).is_null()
                & pl.col("total_student_count").is_not_null()
                & pl.all_horizontal([pl.col(c).is_not_null() for c in others])
                & within_suppressed_range(candidate)
            )
            .then(candidate)
            .otherwise(pl.col(metric))
            .alias(metric)
        )

    out = out.with_columns(updates)
    fill_exprs = [
        (pl.col(f"_old_{c}").is_null() & pl.col(c).is_not_null())
        .cast(pl.Int8)
        .alias(f"_filled_{c}")
        for c in COUNT_COLS
    ]
    out = out.with_columns(fill_exprs)

    filled = int(
        out.select(sum(pl.col(f"_filled_{c}").sum() for c in COUNT_COLS)).item() or 0
    )
    drop_cols = [f"_old_{c}" for c in COUNT_COLS] + [f"_filled_{c}" for c in COUNT_COLS]
    return out.drop(drop_cols), filled


def apply_grade_rollup_rule(df: pl.DataFrame, metric: str) -> tuple[pl.DataFrame, int]:
    group_keys = ["year", "system", "school", "gender", "ethnicity", "sub_population"]
    agg = df.group_by(group_keys).agg(
        [
            pl.col(metric)
            .filter(pl.col("grade") == "All Grades")
            .max()
            .alias("_parent"),
            pl.col(metric)
            .filter(pl.col("grade") != "All Grades")
            .drop_nulls()
            .sum()
            .alias("_children_known_sum"),
            pl.col(metric)
            .filter(pl.col("grade") != "All Grades")
            .is_null()
            .sum()
            .alias("_children_missing"),
            pl.col(metric)
            .filter(pl.col("grade") != "All Grades")
            .len()
            .alias("_children_rows"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col(metric).alias("_old_metric")]
    )

    candidate = (
        pl.when(
            (pl.col("grade") == "All Grades")
            & pl.col(metric).is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 0)
        )
        .then(pl.col("_children_known_sum").fill_null(0))
        .when(
            (pl.col("grade") != "All Grades")
            & pl.col(metric).is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 1)
            & pl.col("_parent").is_not_null()
        )
        .then(pl.col("_parent") - pl.col("_children_known_sum").fill_null(0))
        .otherwise(None)
    )

    out = (
        tmp.with_columns(
            [
                pl.when(
                    pl.col(metric).is_null()
                    & candidate.is_not_null()
                    & within_suppressed_range(candidate)
                )
                .then(candidate)
                .otherwise(pl.col(metric))
                .alias(metric)
            ]
        )
        .drop(["_parent", "_children_known_sum", "_children_missing", "_children_rows"])
        .with_columns(
            [
                (pl.col("_old_metric").is_null() & pl.col(metric).is_not_null())
                .cast(pl.Int8)
                .alias("_filled")
            ]
        )
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(["_old_metric", "_filled"]), filled


def apply_system_rollup_rule(df: pl.DataFrame, metric: str) -> tuple[pl.DataFrame, int]:
    group_keys = ["year", "system", "grade", "gender", "ethnicity", "sub_population"]
    is_parent = pl.col("school") == pl.col("system")
    is_child = pl.col("school").is_not_null() & (pl.col("school") != pl.col("system"))

    agg = df.group_by(group_keys).agg(
        [
            pl.col(metric).filter(is_parent).max().alias("_parent"),
            pl.col(metric)
            .filter(is_child)
            .drop_nulls()
            .sum()
            .alias("_children_known_sum"),
            pl.col(metric).filter(is_child).is_null().sum().alias("_children_missing"),
            pl.col(metric).filter(is_child).len().alias("_children_rows"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col(metric).alias("_old_metric")]
    )

    candidate = (
        pl.when(
            (pl.col("school") == pl.col("system"))
            & pl.col(metric).is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 0)
        )
        .then(pl.col("_children_known_sum").fill_null(0))
        .when(
            (pl.col("school") != pl.col("system"))
            & pl.col(metric).is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 1)
            & pl.col("_parent").is_not_null()
        )
        .then(pl.col("_parent") - pl.col("_children_known_sum").fill_null(0))
        .otherwise(None)
    )

    out = (
        tmp.with_columns(
            [
                pl.when(
                    pl.col(metric).is_null()
                    & candidate.is_not_null()
                    & within_suppressed_range(candidate)
                )
                .then(candidate)
                .otherwise(pl.col(metric))
                .alias(metric)
            ]
        )
        .drop(["_parent", "_children_known_sum", "_children_missing", "_children_rows"])
        .with_columns(
            [
                (pl.col("_old_metric").is_null() & pl.col(metric).is_not_null())
                .cast(pl.Int8)
                .alias("_filled")
            ]
        )
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(["_old_metric", "_filled"]), filled


def apply_demographic_pass(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    out = df
    total_filled = 0

    for metric in COUNT_COLS:
        out, fills = apply_vertical_rule(
            out,
            metric,
            "gender",
            ["year", "system", "school", "grade", "ethnicity", "sub_population"],
            "Male",
            "Female",
            "All Gender",
        )
        total_filled += fills

        out, fills = apply_vertical_rule(
            out,
            metric,
            "ethnicity",
            ["year", "system", "school", "grade", "gender", "sub_population"],
            "Hispanic/Latino",
            "Other Ethnicity",
            "All Ethnicity",
        )
        total_filled += fills

        out, fills = apply_vertical_rule(
            out,
            metric,
            "sub_population",
            ["year", "system", "school", "grade", "gender", "ethnicity"],
            "General Education Students",
            "Students with Disabilities",
            "All SubPopulation",
        )
        total_filled += fills

    out, fills = apply_horizontal_race_rule(out)
    total_filled += fills
    return out, total_filled


def apply_grade_rollup_pass(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    out = df
    total_filled = 0
    for metric in COUNT_COLS:
        out, fills = apply_grade_rollup_rule(out, metric)
        total_filled += fills
    return out, total_filled


def apply_system_rollup_pass(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    out = df
    total_filled = 0
    for metric in COUNT_COLS:
        out, fills = apply_system_rollup_rule(out, metric)
        total_filled += fills
    return out, total_filled


def make_diagnostic_row(
    run_id: str,
    run_started_at: datetime,
    year: str,
    scope_type: str,
    scope_value: str,
    iteration: int,
    pass_name: str,
    cells_filled: int,
    rows_processed: int,
    remaining_null_cells: int,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "run_started_at": run_started_at,
        "run_finished_at": datetime.now(UTC),
        "year": int(year) if year.isdigit() else None,
        "scope_type": scope_type,
        "scope_value": scope_value,
        "iteration": iteration,
        "pass_name": pass_name,
        "cells_filled": cells_filled,
        "rows_processed": rows_processed,
        "remaining_null_cells": remaining_null_cells,
    }


def iterative_impute(
    df: pl.DataFrame,
    run_id: str,
    run_started_at: datetime,
    scope_type: str,
    scope_value: str,
    year: str,
    max_iter: int = 35,
) -> tuple[pl.DataFrame, int, list[dict[str, object]]]:
    out = df
    total_filled = 0
    diagnostics: list[dict[str, object]] = []

    for iteration in range(1, max_iter + 1):
        filled_in_iteration = 0

        out, pass_filled = apply_demographic_pass(out)
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "demographic",
                pass_filled,
                out.height,
                count_null_cells(out),
            )
        )

        out, pass_filled = apply_grade_rollup_pass(out)
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "grade_rollup",
                pass_filled,
                out.height,
                count_null_cells(out),
            )
        )

        out, pass_filled = apply_system_rollup_pass(out)
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "system_rollup",
                pass_filled,
                out.height,
                count_null_cells(out),
            )
        )

        total_filled += filled_in_iteration
        if filled_in_iteration == 0:
            break

    return out, total_filled, diagnostics


def apply_long_pair_rule(
    df: pl.DataFrame,
    dim_col: str,
    left_value: str,
    right_value: str,
    total_value: str,
) -> tuple[pl.DataFrame, int]:
    group_keys = [
        "year",
        "system",
        "school",
        "grade",
        "gender",
        "ethnicity",
        "race",
        "sub_population",
    ]
    group_keys.remove(dim_col)

    agg = df.group_by(group_keys).agg(
        [
            pl.col("count").filter(pl.col(dim_col) == left_value).max().alias("_left"),
            pl.col("count")
            .filter(pl.col(dim_col) == right_value)
            .max()
            .alias("_right"),
            pl.col("count")
            .filter(pl.col(dim_col) == total_value)
            .max()
            .alias("_total"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col("count").alias("_old_count")]
    )

    candidate = (
        pl.when(
            (pl.col(dim_col) == left_value)
            & pl.col("count").is_null()
            & pl.col("_total").is_not_null()
            & pl.col("_right").is_not_null()
        )
        .then(pl.col("_total") - pl.col("_right"))
        .when(
            (pl.col(dim_col) == right_value)
            & pl.col("count").is_null()
            & pl.col("_total").is_not_null()
            & pl.col("_left").is_not_null()
        )
        .then(pl.col("_total") - pl.col("_left"))
        .when(
            (pl.col(dim_col) == total_value)
            & pl.col("count").is_null()
            & pl.col("_left").is_not_null()
            & pl.col("_right").is_not_null()
        )
        .then(pl.col("_left") + pl.col("_right"))
        .otherwise(None)
    )

    out = tmp.with_columns(
        [
            pl.when(
                pl.col("count").is_null()
                & candidate.is_not_null()
                & within_suppressed_range(candidate)
            )
            .then(candidate)
            .otherwise(pl.col("count"))
            .alias("count")
        ]
    ).with_columns(
        [
            (pl.col("_old_count").is_null() & pl.col("count").is_not_null())
            .cast(pl.Int8)
            .alias("_filled")
        ]
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(["_left", "_right", "_total", "_old_count", "_filled"]), filled


def apply_long_race_rule(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    group_keys = [
        "year",
        "system",
        "school",
        "grade",
        "gender",
        "ethnicity",
        "sub_population",
    ]
    agg = df.group_by(group_keys).agg(
        [
            pl.col("count").filter(pl.col("race") == "all_races").max().alias("_all"),
            pl.col("count").filter(pl.col("race") == "asian").max().alias("_asian"),
            pl.col("count")
            .filter(pl.col("race") == "black_or_african_american")
            .max()
            .alias("_black"),
            pl.col("count")
            .filter(pl.col("race") == "american_indian_alaska_native")
            .max()
            .alias("_aian"),
            pl.col("count")
            .filter(pl.col("race") == "native_hawaiian_pacific_islander")
            .max()
            .alias("_nhpi"),
            pl.col("count").filter(pl.col("race") == "white").max().alias("_white"),
            pl.col("count")
            .filter(pl.col("race") == "two_or_more_races")
            .max()
            .alias("_two"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col("count").alias("_old_count")]
    )

    all_children_sum = (
        pl.col("_asian")
        + pl.col("_black")
        + pl.col("_aian")
        + pl.col("_nhpi")
        + pl.col("_white")
        + pl.col("_two")
    )

    candidate = (
        pl.when(
            (pl.col("race") == "all_races")
            & pl.col("count").is_null()
            & pl.col("_asian").is_not_null()
            & pl.col("_black").is_not_null()
            & pl.col("_aian").is_not_null()
            & pl.col("_nhpi").is_not_null()
            & pl.col("_white").is_not_null()
            & pl.col("_two").is_not_null()
        )
        .then(all_children_sum)
        .when(
            (pl.col("race") == "asian")
            & pl.col("count").is_null()
            & pl.col("_all").is_not_null()
            & pl.col("_black").is_not_null()
            & pl.col("_aian").is_not_null()
            & pl.col("_nhpi").is_not_null()
            & pl.col("_white").is_not_null()
            & pl.col("_two").is_not_null()
        )
        .then(
            pl.col("_all")
            - (
                pl.col("_black")
                + pl.col("_aian")
                + pl.col("_nhpi")
                + pl.col("_white")
                + pl.col("_two")
            )
        )
        .when(
            (pl.col("race") == "black_or_african_american")
            & pl.col("count").is_null()
            & pl.col("_all").is_not_null()
            & pl.col("_asian").is_not_null()
            & pl.col("_aian").is_not_null()
            & pl.col("_nhpi").is_not_null()
            & pl.col("_white").is_not_null()
            & pl.col("_two").is_not_null()
        )
        .then(
            pl.col("_all")
            - (
                pl.col("_asian")
                + pl.col("_aian")
                + pl.col("_nhpi")
                + pl.col("_white")
                + pl.col("_two")
            )
        )
        .when(
            (pl.col("race") == "american_indian_alaska_native")
            & pl.col("count").is_null()
            & pl.col("_all").is_not_null()
            & pl.col("_asian").is_not_null()
            & pl.col("_black").is_not_null()
            & pl.col("_nhpi").is_not_null()
            & pl.col("_white").is_not_null()
            & pl.col("_two").is_not_null()
        )
        .then(
            pl.col("_all")
            - (
                pl.col("_asian")
                + pl.col("_black")
                + pl.col("_nhpi")
                + pl.col("_white")
                + pl.col("_two")
            )
        )
        .when(
            (pl.col("race") == "native_hawaiian_pacific_islander")
            & pl.col("count").is_null()
            & pl.col("_all").is_not_null()
            & pl.col("_asian").is_not_null()
            & pl.col("_black").is_not_null()
            & pl.col("_aian").is_not_null()
            & pl.col("_white").is_not_null()
            & pl.col("_two").is_not_null()
        )
        .then(
            pl.col("_all")
            - (
                pl.col("_asian")
                + pl.col("_black")
                + pl.col("_aian")
                + pl.col("_white")
                + pl.col("_two")
            )
        )
        .when(
            (pl.col("race") == "white")
            & pl.col("count").is_null()
            & pl.col("_all").is_not_null()
            & pl.col("_asian").is_not_null()
            & pl.col("_black").is_not_null()
            & pl.col("_aian").is_not_null()
            & pl.col("_nhpi").is_not_null()
            & pl.col("_two").is_not_null()
        )
        .then(
            pl.col("_all")
            - (
                pl.col("_asian")
                + pl.col("_black")
                + pl.col("_aian")
                + pl.col("_nhpi")
                + pl.col("_two")
            )
        )
        .when(
            (pl.col("race") == "two_or_more_races")
            & pl.col("count").is_null()
            & pl.col("_all").is_not_null()
            & pl.col("_asian").is_not_null()
            & pl.col("_black").is_not_null()
            & pl.col("_aian").is_not_null()
            & pl.col("_nhpi").is_not_null()
            & pl.col("_white").is_not_null()
        )
        .then(
            pl.col("_all")
            - (
                pl.col("_asian")
                + pl.col("_black")
                + pl.col("_aian")
                + pl.col("_nhpi")
                + pl.col("_white")
            )
        )
        .otherwise(None)
    )

    out = tmp.with_columns(
        [
            pl.when(
                pl.col("count").is_null()
                & candidate.is_not_null()
                & within_suppressed_range(candidate)
            )
            .then(candidate)
            .otherwise(pl.col("count"))
            .alias("count")
        ]
    ).with_columns(
        [
            (pl.col("_old_count").is_null() & pl.col("count").is_not_null())
            .cast(pl.Int8)
            .alias("_filled")
        ]
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(
        [
            "_all",
            "_asian",
            "_black",
            "_aian",
            "_nhpi",
            "_white",
            "_two",
            "_old_count",
            "_filled",
        ]
    ), filled


def apply_long_grade_rollup_rule(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    group_keys = [
        "year",
        "system",
        "school",
        "gender",
        "ethnicity",
        "race",
        "sub_population",
    ]
    agg = df.group_by(group_keys).agg(
        [
            pl.col("count")
            .filter(pl.col("grade") == "All Grades")
            .max()
            .alias("_parent"),
            pl.col("count")
            .filter(pl.col("grade") != "All Grades")
            .drop_nulls()
            .sum()
            .alias("_children_known_sum"),
            pl.col("count")
            .filter(pl.col("grade") != "All Grades")
            .is_null()
            .sum()
            .alias("_children_missing"),
            pl.col("count")
            .filter(pl.col("grade") != "All Grades")
            .len()
            .alias("_children_rows"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col("count").alias("_old_count")]
    )

    candidate = (
        pl.when(
            (pl.col("grade") == "All Grades")
            & pl.col("count").is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 0)
        )
        .then(pl.col("_children_known_sum").fill_null(0))
        .when(
            (pl.col("grade") != "All Grades")
            & pl.col("count").is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 1)
            & pl.col("_parent").is_not_null()
        )
        .then(pl.col("_parent") - pl.col("_children_known_sum").fill_null(0))
        .otherwise(None)
    )

    out = tmp.with_columns(
        [
            pl.when(
                pl.col("count").is_null()
                & candidate.is_not_null()
                & within_suppressed_range(candidate)
            )
            .then(candidate)
            .otherwise(pl.col("count"))
            .alias("count")
        ]
    ).with_columns(
        [
            (pl.col("_old_count").is_null() & pl.col("count").is_not_null())
            .cast(pl.Int8)
            .alias("_filled")
        ]
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(
        [
            "_parent",
            "_children_known_sum",
            "_children_missing",
            "_children_rows",
            "_old_count",
            "_filled",
        ]
    ), filled


def apply_long_system_rollup_rule(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    group_keys = [
        "year",
        "system",
        "grade",
        "gender",
        "ethnicity",
        "race",
        "sub_population",
    ]
    is_parent = pl.col("school") == pl.col("system")
    is_child = pl.col("school").is_not_null() & (pl.col("school") != pl.col("system"))

    agg = df.group_by(group_keys).agg(
        [
            pl.col("count").filter(is_parent).max().alias("_parent"),
            pl.col("count")
            .filter(is_child)
            .drop_nulls()
            .sum()
            .alias("_children_known_sum"),
            pl.col("count").filter(is_child).is_null().sum().alias("_children_missing"),
            pl.col("count").filter(is_child).len().alias("_children_rows"),
        ]
    )

    tmp = df.join(agg, on=group_keys, how="left").with_columns(
        [pl.col("count").alias("_old_count")]
    )

    candidate = (
        pl.when(
            (pl.col("school") == pl.col("system"))
            & pl.col("count").is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 0)
        )
        .then(pl.col("_children_known_sum").fill_null(0))
        .when(
            (pl.col("school") != pl.col("system"))
            & pl.col("count").is_null()
            & (pl.col("_children_rows") > 0)
            & (pl.col("_children_missing") == 1)
            & pl.col("_parent").is_not_null()
        )
        .then(pl.col("_parent") - pl.col("_children_known_sum").fill_null(0))
        .otherwise(None)
    )

    out = tmp.with_columns(
        [
            pl.when(
                pl.col("count").is_null()
                & candidate.is_not_null()
                & within_suppressed_range(candidate)
            )
            .then(candidate)
            .otherwise(pl.col("count"))
            .alias("count")
        ]
    ).with_columns(
        [
            (pl.col("_old_count").is_null() & pl.col("count").is_not_null())
            .cast(pl.Int8)
            .alias("_filled")
        ]
    )

    filled = int(out.select(pl.col("_filled").sum()).item() or 0)
    return out.drop(
        [
            "_parent",
            "_children_known_sum",
            "_children_missing",
            "_children_rows",
            "_old_count",
            "_filled",
        ]
    ), filled


def iterative_impute_long(
    df: pl.DataFrame,
    run_id: str,
    run_started_at: datetime,
    scope_type: str,
    scope_value: str,
    year: str,
    max_iter: int = 20,
) -> tuple[pl.DataFrame, int, list[dict[str, object]]]:
    out = df
    total_filled = 0
    diagnostics: list[dict[str, object]] = []

    for iteration in range(1, max_iter + 1):
        filled_in_iteration = 0

        out, pass_filled = apply_long_pair_rule(
            out, "gender", "Male", "Female", "All Gender"
        )
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "long_gender",
                pass_filled,
                out.height,
                count_null_long_cells(out),
            )
        )

        out, pass_filled = apply_long_pair_rule(
            out,
            "ethnicity",
            "Hispanic/Latino",
            "Other Ethnicity",
            "All Ethnicity",
        )
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "long_ethnicity",
                pass_filled,
                out.height,
                count_null_long_cells(out),
            )
        )

        out, pass_filled = apply_long_pair_rule(
            out,
            "sub_population",
            "General Education Students",
            "Students with Disabilities",
            "All SubPopulation",
        )
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "long_sub_population",
                pass_filled,
                out.height,
                count_null_long_cells(out),
            )
        )

        out, pass_filled = apply_long_race_rule(out)
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "long_race",
                pass_filled,
                out.height,
                count_null_long_cells(out),
            )
        )

        out, pass_filled = apply_long_grade_rollup_rule(out)
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "long_grade_rollup",
                pass_filled,
                out.height,
                count_null_long_cells(out),
            )
        )

        out, pass_filled = apply_long_system_rollup_rule(out)
        filled_in_iteration += pass_filled
        diagnostics.append(
            make_diagnostic_row(
                run_id,
                run_started_at,
                year,
                scope_type,
                scope_value,
                iteration,
                "long_system_rollup",
                pass_filled,
                out.height,
                count_null_long_cells(out),
            )
        )

        total_filled += filled_in_iteration
        if filled_in_iteration == 0:
            break

    return out, total_filled, diagnostics


def to_long_race(df: pl.DataFrame) -> pl.DataFrame:
    base = df.select(KEY_COLS + COUNT_COLS).unique(subset=KEY_COLS, keep="first")
    frames: list[pl.DataFrame] = []

    for race_name, source_col in RACE_MAP:
        frames.append(
            base.select(
                [
                    pl.col("year"),
                    pl.col("system"),
                    pl.col("school"),
                    pl.col("grade"),
                    pl.col("gender"),
                    pl.col("ethnicity"),
                    pl.lit(race_name).alias("race"),
                    pl.col("sub_population"),
                    pl.col(source_col).alias("count"),
                ]
            )
        )

    return pl.concat(frames, how="vertical").with_columns(
        [
            pl.col("year").cast(pl.Int32, strict=False),
            pl.col("count").cast(pl.Int64, strict=False),
        ]
    )


def ensure_output_tables(
    db_uri: str, target_table: str, diagnostics_table: str
) -> None:
    empty_long = pl.DataFrame(
        {
            "year": pl.Series([], dtype=pl.Int32),
            "system": pl.Series([], dtype=pl.String),
            "school": pl.Series([], dtype=pl.String),
            "grade": pl.Series([], dtype=pl.String),
            "gender": pl.Series([], dtype=pl.String),
            "ethnicity": pl.Series([], dtype=pl.String),
            "race": pl.Series([], dtype=pl.String),
            "sub_population": pl.Series([], dtype=pl.String),
            "count": pl.Series([], dtype=pl.Int64),
        }
    )

    empty_diag = pl.DataFrame(
        {
            "run_id": pl.Series([], dtype=pl.String),
            "run_started_at": pl.Series([], dtype=pl.Datetime(time_zone="UTC")),
            "run_finished_at": pl.Series([], dtype=pl.Datetime(time_zone="UTC")),
            "year": pl.Series([], dtype=pl.Int32),
            "scope_type": pl.Series([], dtype=pl.String),
            "scope_value": pl.Series([], dtype=pl.String),
            "iteration": pl.Series([], dtype=pl.Int32),
            "pass_name": pl.Series([], dtype=pl.String),
            "cells_filled": pl.Series([], dtype=pl.Int64),
            "rows_processed": pl.Series([], dtype=pl.Int64),
            "remaining_null_cells": pl.Series([], dtype=pl.Int64),
        }
    )

    empty_long.write_database(
        table_name=target_table,
        connection=db_uri,
        if_table_exists="replace",
        engine="adbc",
    )
    empty_diag.write_database(
        table_name=diagnostics_table,
        connection=db_uri,
        if_table_exists="replace",
        engine="adbc",
    )


def fetch_scope_data(db_uri: str, source_table: str, scope: Scope) -> pl.DataFrame:
    where_parts = [f"year = '{scope.year}'"]
    if scope.system is not None:
        escaped = scope.system.replace("'", "''")
        where_parts.append(f"system = '{escaped}'")
    if scope.district_only:
        where_parts.append("school = system")

    query = f"SELECT * FROM {source_table} WHERE {' AND '.join(where_parts)};"
    with psycopg.connect(db_uri) as conn:
        return pl.read_database(query=query, connection=conn)


def process_scope(
    db_uri: str,
    source_table: str,
    target_table: str,
    diagnostics_table: str,
    scope: Scope,
    run_id: str,
    run_started_at: datetime,
    first_write: bool,
    persist: bool = True,
) -> tuple[int, int, int, bool]:
    raw = fetch_scope_data(db_uri, source_table, scope)
    if raw.is_empty():
        return 0, 0, 0, first_write

    raw = raw.unique(subset=KEY_COLS, keep="first", maintain_order=True)
    numeric_df = raw.select(KEY_COLS + COUNT_COLS).with_columns(
        [normalize_count_expr(c).alias(c) for c in COUNT_COLS]
    )

    scope_type = "year"
    scope_value = scope.year
    if scope.system is None and scope.district_only:
        scope_type = "year_district_only"
    if scope.system is not None:
        scope_type = "year_system"
        scope_value = f"{scope.year}|{scope.system}"

    numeric_after, filled_cells, diag_rows = iterative_impute(
        numeric_df,
        run_id,
        run_started_at,
        scope_type,
        scope_value,
        scope.year,
    )

    long_out = to_long_race(numeric_after)

    long_after, long_filled_cells, long_diag_rows = iterative_impute_long(
        long_out,
        run_id,
        run_started_at,
        scope_type,
        scope_value,
        scope.year,
    )

    total_filled = filled_cells + long_filled_cells
    diag_df = pl.DataFrame(diag_rows + long_diag_rows)

    if persist:
        write_mode = "replace" if first_write else "append"
        long_after.write_database(
            table_name=target_table,
            connection=db_uri,
            if_table_exists=write_mode,
            engine="adbc",
        )
        diag_df.write_database(
            table_name=diagnostics_table,
            connection=db_uri,
            if_table_exists=write_mode,
            engine="adbc",
        )
        next_first_write = False
    else:
        next_first_write = first_write

    return (
        long_after.height,
        total_filled,
        count_null_long_cells(long_after),
        next_first_write,
    )


def fetch_year_stats(db_uri: str, source_table: str) -> pl.DataFrame:
    with psycopg.connect(db_uri) as conn:
        return pl.read_database(
            query=f"""
                SELECT year, COUNT(*)::bigint AS row_count
                FROM {source_table}
                WHERE year IS NOT NULL
                GROUP BY year
                ORDER BY year
            """,
            connection=conn,
        )


def fetch_systems_for_year(db_uri: str, source_table: str, year: str) -> list[str]:
    with psycopg.connect(db_uri) as conn:
        systems = pl.read_database(
            query=f"""
                SELECT DISTINCT system
                FROM {source_table}
                WHERE year = '{year}'
                  AND system IS NOT NULL
                ORDER BY system
            """,
            connection=conn,
        )
    return systems.get_column("system").to_list()


def cleanup_stale_tables(db_uri: str) -> None:
    with psycopg.connect(db_uri) as conn:
        with conn.cursor() as cur:
            for table_name in STALE_TABLES:
                schema_name, rel_name = table_name.split(".", 1)
                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}.{};").format(
                        sql.Identifier(schema_name),
                        sql.Identifier(rel_name),
                    )
                )
        conn.commit()


def run(
    db_uri: str,
    source_table: str,
    target_table: str,
    diagnostics_table: str,
    year_row_threshold: int,
) -> None:
    run_id = str(uuid4())
    run_started_at = datetime.now(UTC)

    ensure_output_tables(db_uri, target_table, diagnostics_table)
    years = fetch_year_stats(db_uri, source_table)

    total_rows = 0
    total_filled = 0
    first_write = True

    for row in years.iter_rows(named=True):
        year = row["year"]
        row_count = int(row["row_count"])

        print(f"\n=== Year {year} ({row_count} rows) ===")

        if row_count <= year_row_threshold:
            try:
                rows, filled, unresolved, first_write = process_scope(
                    db_uri,
                    source_table,
                    target_table,
                    diagnostics_table,
                    Scope(year=year),
                    run_id,
                    run_started_at,
                    first_write,
                )
                print(
                    f"Processed year scope: rows={rows}, imputed_cells={filled}, unresolved_cells={unresolved}"
                )
                total_rows += rows
                total_filled += filled
                continue
            except Exception as exc:
                print(f"Year-level scope failed for {year}: {exc}")
                print("Falling back to district-only then per-system chunks.")

        rows, filled, unresolved, first_write = process_scope(
            db_uri,
            source_table,
            target_table,
            diagnostics_table,
            Scope(year=year, district_only=True),
            run_id,
            run_started_at,
            first_write,
            persist=False,
        )
        print(
            f"District-only scope (analysis only): rows={rows}, imputed_cells={filled}, unresolved_cells={unresolved}"
        )

        for system in fetch_systems_for_year(db_uri, source_table, year):
            rows, filled, unresolved, first_write = process_scope(
                db_uri,
                source_table,
                target_table,
                diagnostics_table,
                Scope(year=year, system=system, district_only=False),
                run_id,
                run_started_at,
                first_write,
            )
            print(
                f"System scope {system}: rows={rows}, imputed_cells={filled}, unresolved_cells={unresolved}"
            )
            total_rows += rows
            total_filled += filled

    cleanup_stale_tables(db_uri)

    print("\n=== Run Complete ===")
    print(f"run_id={run_id}")
    print(f"rows_written={total_rows}")
    print(f"imputed_cells={total_filled}")
    print(f"target_table={target_table}")
    print(f"diagnostics_table={diagnostics_table}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Polars hierarchical imputation for student demographics"
    )
    parser.add_argument("--db-uri", default=DB_URI)
    parser.add_argument("--source-table", default=SOURCE_TABLE)
    parser.add_argument("--target-table", default=TARGET_TABLE)
    parser.add_argument("--diagnostics-table", default=DIAGNOSTICS_TABLE)
    parser.add_argument(
        "--year-row-threshold",
        type=int,
        default=550000,
        help="Max rows to process in a single year chunk before fallback",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        db_uri=args.db_uri,
        source_table=args.source_table,
        target_table=args.target_table,
        diagnostics_table=args.diagnostics_table,
        year_row_threshold=args.year_row_threshold,
    )
