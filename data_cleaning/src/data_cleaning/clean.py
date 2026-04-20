import polars as pl
from pathlib import Path
from decimal import Decimal, InvalidOperation
import re

data_dir = Path(__file__).resolve().parents[3] / "flat_data" / "out"

print(data_dir)

"""
# Edunomics Cleaning

## Steps/Objectives
1. Put it in a db today
- Change column names
- Create a normalized thing for immutable schoool information (location, etc.)
"""


def normalize_id_value(value: object) -> str | None:
    """Normalizes the ID values.

    Args:
        value: dirty value

    Returns:
        Cleaned and formatted value
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    upper = text.upper()
    if upper in {"NA", "NAN", "NULL", "NONE"}:
        return None

    text = text.replace(",", "")

    try:
        dec = Decimal(text)
    except InvalidOperation:
        cleaned = text.rstrip(".0") if text.endswith(".0") else text
        return cleaned or None

    if dec == dec.to_integral_value():
        return str(dec.quantize(Decimal("1")))
    return format(dec.normalize(), "f").rstrip("0").rstrip(".")


def normalize_state_assigned_id(value: object) -> str | None:
    """Cleans the state id.

    Strips out the `AL-` to leave just the integer.
    Uses regex to select the last digit.

    Args:
        value: dirty value

    Returns:
        Cleaned and formatted value
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    upper = text.upper()
    if upper in {"NA", "NAN", "NULL", "NONE"}:
        return None

    text = text.replace(",", "")

    try:
        dec = Decimal(text)
        if dec == dec.to_integral_value():
            number = str(dec.quantize(Decimal("1")))
            return number.lstrip("0") or "0"
    except InvalidOperation:
        pass

    parts = re.findall(r"\d+", text)
    if not parts:
        return None

    return parts[-1].lstrip("0") or "0"


def mode_per_group(
    df: pl.DataFrame, group_keys: list[str], value_col: str
) -> pl.DataFrame:
    """Selects the mode per group.

    Instead of clean -> aggregate until single row per school.

    """
    value_expr = pl.col(value_col)
    valid_mask = value_expr.is_not_null()

    if df.schema.get(value_col) == pl.String:
        valid_mask = valid_mask & (value_expr.str.strip_chars() != "")

    return (
        df.filter(valid_mask)
        .group_by(group_keys + [value_col])
        .agg(
            pl.len().alias("_cnt"),
            pl.col("_row_nr").min().alias("_first_row"),
        )
        .sort(
            by=group_keys + ["_cnt", "_first_row"],
            descending=[False, False, True, False],
        )
        .group_by(group_keys)
        .first()
        .select(group_keys + [value_col])
    )


def main() -> None:
    # %%
    # Accountability
    acc_path = data_dir / "school_accountability.csv"
    acc_df = pl.scan_csv(acc_path).select(["System", "School"]).unique()

    # Edunomics
    edu_path = data_dir / "school_edunomics.csv"
    edu_df = (
        pl.scan_csv(edu_path)
        .select(
            [
                "distid_stateassigned",
                "schoolid_stateassigned",
                "distname",
                "schoolname",
                "ncesdistid_admin",
                "ncesdistid_geo",
                "census_id",
                "ncesid",
                "nces_locale",
                "nces_charter",
                "nces_magnet",
                "nces_address",
                "nces_city",
                "nces_zip",
            ]
        )
        .unique()
        .rename({"distname": "system", "schoolname": "school"})
    )

    # Student Demo
    stu_demo = data_dir / "student_demographics.csv"
    stu_demo_df = pl.scan_csv(stu_demo).select(["System", "School"]).unique()

    # Teacher Demo
    tch_demo = data_dir / "teacher_demographics.csv"
    tch_demo_df = pl.scan_csv(tch_demo).select(["System", "School"]).unique()

    # Teacher Effectiveness
    tch_eff = data_dir / "teacher_effectiveness.csv"
    tch_eff_df = (
        pl.scan_csv(tch_eff)
        .select(["System Code", "System", "School Code", "School"])
        .unique()
        .rename(
            {
                "System Code": "distid_stateassigned",
                "School Code": "schoolid_stateassigned",
            }
        )
    )

    # Teacher Experience
    tch_exp = data_dir / "teacher_experience.csv"
    tch_exp_df = pl.scan_csv(tch_exp).select(["System", "School"]).unique()

    # %%
    frames = [acc_df, edu_df, stu_demo_df, tch_demo_df, tch_eff_df, tch_exp_df]
    frames_lower = [df.select(pl.all().name.to_lowercase()) for df in frames]

    # Diagonal relaxed concat and unique
    input_df = pl.concat(frames_lower, how="diagonal_relaxed").unique().collect()

    text_columns = ["system", "school", "nces_city", "nces_address"]
    categorical_columns = ["nces_locale", "nces_charter", "nces_magnet"]

    df = input_df.with_columns(
        [
            pl.when(pl.col(col).is_not_null())
            .then(pl.col(col).cast(pl.String).str.strip_chars().str.to_titlecase())
            .otherwise(None)
            .alias(col)
            for col in text_columns
            if col in input_df.columns
        ]
    )

    state_assigned_columns = ["distid_stateassigned", "schoolid_stateassigned"]
    present_state_assigned_columns = [
        col for col in state_assigned_columns if col in df.columns
    ]

    if present_state_assigned_columns:
        df = df.with_columns(
            [
                pl.col(col)
                .map_elements(normalize_state_assigned_id, return_dtype=pl.String)
                .alias(col)
                for col in present_state_assigned_columns
            ]
        )

    string_columns = [name for name, dtype in df.schema.items() if dtype == pl.String]
    if string_columns:
        df = df.with_columns(
            [
                pl.when(pl.col(col).is_not_null())
                .then(pl.col(col).str.replace_all(r" {2,}", " "))
                .otherwise(None)
                .alias(col)
                for col in string_columns
            ]
        )

    for col in categorical_columns:
        if col not in df.columns:
            continue

        df = df.with_columns(
            pl.when(pl.col(col).is_not_null())
            .then(
                pl.col(col)
                .cast(pl.String)
                .str.strip_chars()
                .str.replace(r"^\d+\s*-\s*", "", literal=False)
            )
            .otherwise(None)
            .alias(col)
        )

        null_count = df.select(pl.col(col).is_null().sum()).item()
        blank_count = df.select(
            pl.when(pl.col(col).is_not_null())
            .then(pl.col(col).str.strip_chars() == "")
            .otherwise(False)
            .sum()
        ).item()
        replace_with_blank = blank_count >= null_count

        if replace_with_blank:
            df = df.with_columns(
                pl.when(pl.col(col).str.to_uppercase() == "NA")
                .then(pl.lit(""))
                .otherwise(pl.col(col))
                .alias(col)
            )
        else:
            df = df.with_columns(
                pl.when(pl.col(col).str.to_uppercase() == "NA")
                .then(pl.lit(None, dtype=pl.String))
                .otherwise(pl.col(col))
                .alias(col)
            )

    system_lookup = (
        df.filter(
            pl.col("school").is_not_null() & (pl.col("school").str.strip_chars() != "")
        )
        .filter(
            pl.col("system").is_not_null() & (pl.col("system").str.strip_chars() != "")
        )
        .with_row_index("_row_nr")
        .group_by(["school", "system"])
        .agg(
            pl.len().alias("_cnt"),
            pl.col("_row_nr").min().alias("_first_row"),
        )
        .sort(by=["school", "_cnt", "_first_row"], descending=[False, True, False])
        .group_by("school")
        .first()
        .select(["school", pl.col("system").alias("_filled_system")])
    )

    df = (
        df.join(system_lookup, on="school", how="left")
        .with_columns(
            pl.when(
                pl.col("system").is_null() | (pl.col("system").str.strip_chars() == "")
            )
            .then(pl.col("_filled_system"))
            .otherwise(pl.col("system"))
            .alias("system")
        )
        .drop("_filled_system")
    )

    df = df.filter(
        pl.col("system").is_not_null()
        & pl.col("school").is_not_null()
        & (pl.col("system").str.strip_chars() != "")
        & (pl.col("school").str.strip_chars() != "")
        & (pl.col("system") != pl.col("school"))
    )

    df = df.with_row_index("_row_nr")

    group_keys = ["system", "school"]
    other_columns = [c for c in df.columns if c not in group_keys + ["_row_nr"]]

    result = df.select(group_keys).unique().sort(group_keys)

    for col in other_columns:
        mode_df = mode_per_group(df, group_keys, col)
        result = result.join(mode_df, on=group_keys, how="left")

    id_like_columns = [
        col
        for col in result.columns
        if ("id" in col.lower() or col.lower() == "nces_zip")
    ]

    if id_like_columns:
        result = result.with_columns(
            [
                pl.col(col)
                .map_elements(normalize_id_value, return_dtype=pl.String)
                .alias(col)
                for col in id_like_columns
            ]
        )

    result = result.sort(group_keys)

    output_path = "normalized_schools.csv"
    result.write_csv(output_path)

    print(f"Wrote {result.height} rows to {output_path}")


if __name__ == "__main__":
    main()
