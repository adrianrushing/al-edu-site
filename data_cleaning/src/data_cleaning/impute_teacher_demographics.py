from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import polars as pl
import psycopg

DEFAULT_DB_URI = "postgresql://localhost:5433/eflt"
DB_URI = os.getenv("DATABASE_URL") or os.getenv("DB_URI") or DEFAULT_DB_URI
SOURCE_TABLE = "staging.stg_teacher_demographics"
TARGET_TABLE = "sandbox.impute_teacher_demographics"
DIAG_TABLE = "sandbox.impute_teacher_demographics_diagnostics"

KEY_COLS = ["year", "system", "school", "gender", "race", "ethnicity", "sub_population"]
DIM_RULES = [
    ("gender", ["Male", "Female", "Gender Not Specified"], "All Gender"),
    (
        "ethnicity",
        ["Hispanic/Latino", "Other Ethnicity", "Ethnicity Not Specified"],
        "All Ethnicity",
    ),
    (
        "race",
        [
            "Asian",
            "Black or African American",
            "American Indian/Alaska Native",
            "Native Hawaiian/Pacific Islander",
            "White",
            "Two or more races",
            "Race Not Specified",
        ],
        "All Race",
    ),
]


@dataclass(frozen=True)
class RuleStat:
    iteration: int
    metric: str
    dim_col: str
    filled_cells: int


def read_source() -> pl.DataFrame:
    with psycopg.connect(DB_URI) as conn:
        return pl.read_database(query=f"SELECT * FROM {SOURCE_TABLE};", connection=conn)


def normalize_source(raw: pl.DataFrame) -> pl.DataFrame:
    now = datetime.now()
    dedup = raw.unique(subset=KEY_COLS, keep="first", maintain_order=True)
    return dedup.select(
        [
            *KEY_COLS,
            pl.col("demographic_count")
            .cast(pl.Float64, strict=False)
            .alias("demographic_count_num"),
            pl.col("total_count").cast(pl.Float64, strict=False).alias("total_count_num"),
            pl.col("demographic_rate")
            .cast(pl.Float64, strict=False)
            .alias("demographic_rate_num"),
            pl.col("_source_file"),
            pl.col("_ingested_at"),
            pl.lit(False).alias("imputed_flag"),
            pl.lit(None, dtype=pl.String).alias("imputation_method"),
            pl.lit(now).alias("_processed_at"),
        ]
    )


def build_candidates(
    df: pl.DataFrame,
    metric_col: str,
    dim_col: str,
    children: list[str],
    total_label: str,
) -> pl.DataFrame:
    group_keys = [c for c in KEY_COLS if c != dim_col]

    agg_exprs = [
        pl.col(metric_col).filter(pl.col(dim_col) == total_label).max().alias("_total")
    ]
    for child in children:
        alias = f"_c_{children.index(child)}"
        agg_exprs.append(
            pl.col(metric_col).filter(pl.col(dim_col) == child).max().alias(alias)
        )

    agg = df.group_by(group_keys).agg(agg_exprs)

    child_cols = [f"_c_{i}" for i in range(len(children))]
    missing_count_expr = pl.col(child_cols[0]).is_null().cast(pl.Int64)
    sum_known_expr = pl.col(child_cols[0]).fill_null(0.0)
    for child_col in child_cols[1:]:
        missing_count_expr = missing_count_expr + pl.col(child_col).is_null().cast(
            pl.Int64
        )
        sum_known_expr = sum_known_expr + pl.col(child_col).fill_null(0.0)

    missing_label = pl.lit(None, dtype=pl.String)
    for i, child in enumerate(children):
        missing_label = (
            pl.when(pl.col(child_cols[i]).is_null())
            .then(pl.lit(child))
            .otherwise(missing_label)
        )

    child_candidates = (
        agg.with_columns(
            [
                missing_count_expr.alias("_missing_children"),
                sum_known_expr.alias("_sum_known"),
            ]
        )
        .filter((pl.col("_total").is_not_null()) & (pl.col("_missing_children") == 1))
        .with_columns(
            [
                missing_label.alias(dim_col),
                (pl.col("_total") - pl.col("_sum_known")).alias("candidate"),
            ]
        )
        .filter(pl.col("candidate") >= 0)
        .select(group_keys + [dim_col, "candidate"])
    )

    total_candidates = (
        agg.with_columns(
            [
                missing_count_expr.alias("_missing_children"),
                sum_known_expr.alias("_sum_known"),
            ]
        )
        .filter((pl.col("_total").is_null()) & (pl.col("_missing_children") == 0))
        .with_columns(
            [
                pl.lit(total_label).alias(dim_col),
                pl.col("_sum_known").alias("candidate"),
            ]
        )
        .select(group_keys + [dim_col, "candidate"])
    )

    return pl.concat([child_candidates, total_candidates], how="vertical").unique(
        subset=group_keys + [dim_col], keep="first"
    )


def apply_candidates(
    df: pl.DataFrame,
    metric_col: str,
    candidates: pl.DataFrame,
    method_name: str,
) -> tuple[pl.DataFrame, int]:
    if candidates.is_empty():
        return df, 0

    existing_keys = df.select(KEY_COLS).unique()
    candidate_keys = candidates.select(KEY_COLS)

    in_existing = candidate_keys.join(existing_keys, on=KEY_COLS, how="inner")
    missing_rows = candidate_keys.join(existing_keys, on=KEY_COLS, how="anti")

    cand_existing = candidates.join(in_existing, on=KEY_COLS, how="inner")
    cand_missing = candidates.join(missing_rows, on=KEY_COLS, how="inner")

    updated = df.join(
        cand_existing.rename({"candidate": "_cand"}),
        on=KEY_COLS,
        how="left",
    ).with_columns([pl.col(metric_col).is_null().alias("_was_null")])

    updated = updated.with_columns(
        [
            pl.when(pl.col(metric_col).is_null() & pl.col("_cand").is_not_null())
            .then(pl.col("_cand"))
            .otherwise(pl.col(metric_col))
            .alias(metric_col),
            pl.when(pl.col(metric_col).is_null() & pl.col("_cand").is_not_null())
            .then(True)
            .otherwise(pl.col("imputed_flag"))
            .alias("imputed_flag"),
            pl.when(pl.col(metric_col).is_null() & pl.col("_cand").is_not_null())
            .then(pl.lit(method_name))
            .otherwise(pl.col("imputation_method"))
            .alias("imputation_method"),
        ]
    )

    filled_existing = int(
        updated.select(
            (pl.col("_was_null") & pl.col("_cand").is_not_null()).cast(pl.Int64).sum()
        ).item()
        or 0
    )

    updated = updated.drop(["_cand", "_was_null"])

    if cand_missing.is_empty():
        return updated, filled_existing

    now = datetime.now()
    new_rows = cand_missing.select(
        KEY_COLS + [pl.col("candidate").alias(metric_col)]
    ).with_columns(
        [
            pl.lit(None, dtype=pl.Float64).alias("demographic_count_num")
            if metric_col != "demographic_count_num"
            else pl.col("demographic_count_num"),
            pl.lit(None, dtype=pl.Float64).alias("total_count_num")
            if metric_col != "total_count_num"
            else pl.col("total_count_num"),
            pl.lit(None, dtype=pl.Float64).alias("demographic_rate_num"),
            pl.lit("imputed_teacher_demographics").alias("_source_file"),
            pl.lit(now).alias("_ingested_at"),
            pl.lit(True).alias("imputed_flag"),
            pl.lit(method_name).alias("imputation_method"),
            pl.lit(now).alias("_processed_at"),
        ]
    )

    new_rows = new_rows.select(updated.columns)
    return pl.concat(
        [updated, new_rows], how="vertical_relaxed"
    ), filled_existing + new_rows.height


def recompute_rate(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        [
            pl.when(
                pl.col("demographic_count_num").is_not_null()
                & pl.col("total_count_num").is_not_null()
                & (pl.col("total_count_num") > 0)
            )
            .then(
                (pl.col("demographic_count_num") / pl.col("total_count_num") * 100).round(
                    2
                )
            )
            .otherwise(pl.col("demographic_rate_num"))
            .alias("demographic_rate_num")
        ]
    )


def iterative_impute(
    df: pl.DataFrame, max_iter: int = 15
) -> tuple[pl.DataFrame, list[RuleStat]]:
    out = df
    stats: list[RuleStat] = []

    for iteration in range(1, max_iter + 1):
        fills_iteration = 0
        for metric_col in ["demographic_count_num", "total_count_num"]:
            for dim_col, children, total_label in DIM_RULES:
                candidates = build_candidates(
                    out, metric_col, dim_col, children, total_label
                )
                method_name = f"{metric_col}:{dim_col}"
                out, filled = apply_candidates(out, metric_col, candidates, method_name)
                stats.append(
                    RuleStat(
                        iteration=iteration,
                        metric=metric_col,
                        dim_col=dim_col,
                        filled_cells=filled,
                    )
                )
                fills_iteration += filled

        out = recompute_rate(out)
        if fills_iteration == 0:
            break

    return out, stats


def finalize_output(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        [
            pl.col("year").cast(pl.Int32, strict=False),
            pl.col("demographic_count_num").round(2).alias("demographic_count"),
            pl.col("total_count_num").round(2).alias("total_count"),
            pl.col("demographic_rate_num").round(2).alias("demographic_rate"),
        ]
    ).select(
        [
            "year",
            "system",
            "school",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
            "demographic_count",
            "total_count",
            "demographic_rate",
            "imputed_flag",
            "imputation_method",
            "_source_file",
            "_ingested_at",
            "_processed_at",
        ]
    )


def stats_to_df(run_id: str, stats: list[RuleStat], out_df: pl.DataFrame) -> pl.DataFrame:
    now = datetime.now()
    rows = [
        {
            "run_id": run_id,
            "processed_at": now,
            "iteration": s.iteration,
            "metric": s.metric,
            "dimension": s.dim_col,
            "filled_cells": s.filled_cells,
        }
        for s in stats
    ]
    summary = {
        "run_id": run_id,
        "processed_at": now,
        "iteration": 0,
        "metric": "summary",
        "dimension": "all",
        "filled_cells": int(
            out_df.select(pl.col("imputed_flag").cast(pl.Int64).sum()).item() or 0
        ),
    }
    rows.append(summary)
    return pl.DataFrame(rows)


def write_outputs(imputed: pl.DataFrame, diagnostics: pl.DataFrame) -> None:
    imputed.write_database(
        table_name=TARGET_TABLE,
        connection=DB_URI,
        if_table_exists="replace",
        engine="adbc",
    )
    diagnostics.write_database(
        table_name=DIAG_TABLE,
        connection=DB_URI,
        if_table_exists="replace",
        engine="adbc",
    )


def main() -> None:
    run_id = str(uuid4())
    raw = read_source()
    normalized = normalize_source(raw)
    imputed, stats = iterative_impute(normalized)
    finalized = finalize_output(imputed)
    diagnostics = stats_to_df(run_id, stats, finalized)
    write_outputs(finalized, diagnostics)

    total_rows = finalized.height
    imputed_rows = int(
        finalized.select(pl.col("imputed_flag").cast(pl.Int64).sum()).item() or 0
    )
    print(f"run_id={run_id}")
    print(f"rows_written={total_rows}")
    print(f"rows_with_imputation={imputed_rows}")
    print(f"target_table={TARGET_TABLE}")
    print(f"diag_table={DIAG_TABLE}")


if __name__ == "__main__":
    main()
