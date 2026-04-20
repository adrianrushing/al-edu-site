import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full", app_title="Cleaning AL State Data")


@app.cell
def _():
    from pathlib import Path
    from typing import Any

    import marimo as mo
    import polars as pl

    data_dir = Path(__file__).resolve().parents[3] / "flat_data" / "out"

    print(data_dir)
    return data_dir, mo, pl


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Edunomics Cleaning

    ## Steps/Objectives
    1. Put it in a db today
    - Change column names
    - Create a normalized thing for immutable schoool information (location, etc.)
    """)
    return


@app.cell
def _(data_dir, pl):
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
    return acc_df, edu_df, stu_demo_df, tch_demo_df, tch_eff_df, tch_exp_df


@app.cell
def _(acc_df, edu_df, pl, stu_demo_df, tch_demo_df, tch_eff_df, tch_exp_df):
    frames = [acc_df, edu_df, stu_demo_df, tch_demo_df, tch_eff_df, tch_exp_df]
    frames_lower = [df.select(pl.all().name.to_lowercase()) for df in frames]

    # Diagonal relaxed concat and unique
    input = (
        pl.concat(frames_lower, how="diagonal_relaxed")
        .unique()
        .collect()
        .sort(by="school")
    )

    input
    return (input,)


@app.cell
def _(input, pl):
    result = (
        input.with_columns(
            pl.col("schoolid_stateassigned")
            .str.extract(r"(\d+)$", group_index=1)  # extract last numeric segment
            .str.replace(r"^0+", "", literal=False)  # strip all leading zeros
            .alias("schoolid_stateassigned"),
            pl.col("distid_stateassigned")
            .str.extract(r"(\d+)$", group_index=1)
            .str.replace(r"^0+", "", literal=False)
            .alias("distid_stateassigned"),
            pl.col("nces_locale")
            .str.replace_all(r"[\d\-]", "", literal=False)
            .alias("nces_locale"),
            pl.col("nces_charter")
            .str.replace_all(r"[\d\-]", "", literal=False)
            .alias("nces_charter"),
            pl.col("nces_magnet")
            .str.replace_all(r"[\d\-]", "", literal=False)
            .alias("nces_magnet"),
            pl.col("nces_address").str.to_uppercase(),
            pl.col("nces_city").str.to_uppercase(),
        )
        .unique()
        .sort(by="school")
    )
    result = (
        result.group_by(pl.all())
        .len()
        .sort("len", descending=True)
        .group_by("system", "school")
        .first()  # keep the row with the highest count per system/school combo
        .drop("len")
    )
    result

    return


@app.cell
def _(input):
    locale = input.select("nces_locale").unique().sort(by="nces_locale")

    locale
    return


if __name__ == "__main__":
    app.run()
