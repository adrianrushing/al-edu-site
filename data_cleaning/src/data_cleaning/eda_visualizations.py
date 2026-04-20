import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full", app_title="EFLT Demographic Mismatch EDA")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import polars as pl
    import psycopg
    from scipy import stats

    return Path, mo, np, os, pl, plt, psycopg, stats


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Demographic Mismatch vs Achievement

    This notebook compares school demographic composition to county context,
    then tests whether mismatch is associated with achievement.

    - **Default year**: 2024 (selector available)
    - **Geo baseline**: county population demographics from 2021
    - **Goal**: quantify student-area and teacher-area mismatch separately
    """)
    return


@app.cell
def _(mo):
    year_selector = mo.ui.dropdown(
        label="School outcome year",
        options=[2022, 2023, 2024],
        value=2024,
    )
    district_top_n = mo.ui.slider(
        start=5,
        stop=25,
        step=1,
        value=10,
        label="Top districts for box plot",
    )
    min_test_n = mo.ui.slider(
        start=20,
        stop=200,
        step=5,
        value=40,
        label="Minimum sample size for tests",
    )
    mo.hstack([year_selector, district_top_n, min_test_n], justify="start", gap=2)
    return district_top_n, min_test_n, year_selector


@app.cell
def _(Path, os, pl, psycopg):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                if key.strip() == "DATABASE_URL":
                    database_url = value.strip().strip('"').strip("'")
                    break
    if not database_url:
        database_url = "postgresql://localhost:5433/eflt"

    def run_query(query: str, params: tuple | None = None):
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
        return pl.from_dicts([dict(zip(columns, row, strict=False)) for row in rows])

    return (run_query,)


@app.cell
def _(run_query, year_selector):
    outcomes_sql = """
    SELECT
        o.school_key,
        o.year,
        o.ach_all,
        COALESCE(sy.nces_locale_type, 'Unknown') AS locale_type,
        ctx.district_name,
        ctx.county_fips
    FROM core.fact_school_outcomes_wide o
    LEFT JOIN core.vw_school_year_geo_context ctx
      ON ctx.school_key = o.school_key
     AND ctx.year = o.year
    LEFT JOIN core.bridge_school_year sy
      ON sy.school_key = o.school_key
     AND sy.school_year_start = o.year
    WHERE o.year = %s
      AND o.ach_all IS NOT NULL
    """

    student_sql = """
    SELECT
        school_key,
        year,
        all_race_count,
        am_indian_ak_native_count,
        asian_count,
        black_aa_count,
        white_count
    FROM core.mv_student_race_pivot
    WHERE year = %s
      AND grade = 'All Grades'
      AND gender = 'All Gender'
      AND ethnicity = 'All Ethnicity'
      AND sub_population = 'All SubPopulation'
    """

    student_hisp_sql = """
    SELECT
        school_key,
        year,
        all_race_count AS hisp_count
    FROM core.mv_student_race_pivot
    WHERE year = %s
      AND grade = 'All Grades'
      AND gender = 'All Gender'
      AND ethnicity = 'Hispanic/Latino'
      AND sub_population = 'All SubPopulation'
    """

    teacher_sql = """
    SELECT
        school_key,
        year,
        race,
        demographic_count
    FROM core.fact_teacher_demographics
    WHERE year = %s
      AND gender = 'All Gender'
      AND ethnicity = 'All Ethnicity'
      AND sub_population = 'All SubPopulation'
      AND race IN (
          'All Race',
          'American Indian/Alaska Native',
          'Asian',
          'Black or African American',
          'White'
      )
    """

    teacher_hisp_sql = """
    SELECT
        school_key,
        year,
        demographic_count AS hisp_count
    FROM core.fact_teacher_demographics
    WHERE year = %s
      AND race = 'All Race'
      AND gender = 'All Gender'
      AND ethnicity = 'Hispanic/Latino'
      AND sub_population = 'All SubPopulation'
    """

    county_geo_sql = """
    SELECT
        county_fips,
        population_group,
        population_count
    FROM core.fact_geo_population_county
    WHERE year = 2021
      AND population_group IN ('aian', 'asian', 'black', 'white', 'hisp', 'total')
    """

    raw_outcomes_df = run_query(outcomes_sql, (year_selector.value,))
    raw_student_df = run_query(student_sql, (year_selector.value,))
    raw_student_hisp_df = run_query(student_hisp_sql, (year_selector.value,))
    raw_teacher_df = run_query(teacher_sql, (year_selector.value,))
    raw_teacher_hisp_df = run_query(teacher_hisp_sql, (year_selector.value,))
    raw_county_geo_df = run_query(county_geo_sql)
    return (
        raw_county_geo_df,
        raw_outcomes_df,
        raw_student_df,
        raw_student_hisp_df,
        raw_teacher_df,
        raw_teacher_hisp_df,
    )


@app.cell
def _(
    pl,
    raw_county_geo_df,
    raw_outcomes_df,
    raw_student_df,
    raw_student_hisp_df,
    raw_teacher_df,
    raw_teacher_hisp_df,
):
    # Ensure numeric types
    def to_numeric(df, cols):
        return df.with_columns(
            [pl.col(c).cast(pl.Float64, strict=False) for c in cols if c in df.columns]
        )

    outcomes = to_numeric(raw_outcomes_df, ["ach_all"])
    student = to_numeric(
        raw_student_df,
        [
            "all_race_count",
            "am_indian_ak_native_count",
            "asian_count",
            "black_aa_count",
            "white_count",
        ],
    )
    student_hisp = to_numeric(raw_student_hisp_df, ["hisp_count"]).rename(
        {"hisp_count": "student_hisp_count"}
    )
    teacher = to_numeric(raw_teacher_df, ["demographic_count"])
    teacher_hisp = to_numeric(raw_teacher_hisp_df, ["hisp_count"]).rename(
        {"hisp_count": "teacher_hisp_count"}
    )
    county_geo = to_numeric(raw_county_geo_df, ["population_count"])

    # Merge student
    student_features = student.join(
        student_hisp.select(["school_key", "year", "student_hisp_count"]),
        on=["school_key", "year"],
        how="left",
    )

    # Pivot teacher
    teacher_wide = teacher.pivot(
        on="race",
        index=["school_key", "year"],
        values="demographic_count",
        aggregate_function="first",
    ).rename(
        {
            "All Race": "teacher_total",
            "American Indian/Alaska Native": "teacher_aian_count",
            "Asian": "teacher_asian_count",
            "Black or African American": "teacher_black_count",
            "White": "teacher_white_count",
        }
    )

    teacher_features = teacher_wide.join(
        teacher_hisp.select(["school_key", "year", "teacher_hisp_count"]),
        on=["school_key", "year"],
        how="left",
    )

    # Pivot county
    county_geo_wide = county_geo.pivot(
        on="population_group",
        index="county_fips",
        values="population_count",
        aggregate_function="first",
    ).rename(
        {
            "aian": "county_aian_count",
            "asian": "county_asian_count",
            "black": "county_black_count",
            "white": "county_white_count",
            "hisp": "county_hisp_count",
            "total": "county_total",
        }
    )

    # Model DF
    model_df = outcomes.join(student_features, on=["school_key", "year"], how="inner")
    model_df = model_df.join(teacher_features, on=["school_key", "year"], how="inner")
    model_df = model_df.join(county_geo_wide, on="county_fips", how="left")

    # Mismatch calculations
    race_groups = ["aian", "asian", "black", "white"]

    # Calculate shares
    for grp in race_groups:
        s_col = (
            "am_indian_ak_native_count"
            if grp == "aian"
            else ("black_aa_count" if grp == "black" else f"{grp}_count")
        )
        model_df = model_df.with_columns(
            [
                (pl.col(s_col) / pl.col("all_race_count")).alias(f"student_{grp}_share"),
                (pl.col(f"teacher_{grp}_count") / pl.col("teacher_total")).alias(
                    f"teacher_{grp}_share"
                ),
                (pl.col(f"county_{grp}_count") / pl.col("county_total")).alias(
                    f"county_{grp}_share"
                ),
            ]
        )

    model_df = model_df.with_columns(
        [
            (pl.col("student_hisp_count") / pl.col("all_race_count")).alias(
                "student_hisp_share"
            ),
            (pl.col("teacher_hisp_count") / pl.col("teacher_total")).alias(
                "teacher_hisp_share"
            ),
            (pl.col("county_hisp_count") / pl.col("county_total")).alias(
                "county_hisp_share"
            ),
        ]
    )

    # Race Mismatch (sum of abs differences)
    model_df = model_df.with_columns(
        [
            pl.sum_horizontal(
                [
                    (pl.col(f"student_{grp}_share") - pl.col(f"county_{grp}_share")).abs()
                    for grp in race_groups
                ]
            ).alias("student_race_mismatch"),
            pl.sum_horizontal(
                [
                    (pl.col(f"teacher_{grp}_share") - pl.col(f"county_{grp}_share")).abs()
                    for grp in race_groups
                ]
            ).alias("teacher_race_mismatch"),
        ]
    )

    # Hisp Mismatch
    model_df = model_df.with_columns(
        [
            (pl.col("student_hisp_share") - pl.col("county_hisp_share"))
            .abs()
            .alias("student_hisp_mismatch"),
            (pl.col("teacher_hisp_share") - pl.col("county_hisp_share"))
            .abs()
            .alias("teacher_hisp_mismatch"),
        ]
    )

    # Final Mismatch
    model_df = model_df.with_columns(
        [
            (
                (pl.col("student_race_mismatch") + pl.col("student_hisp_mismatch")) / 2.0
            ).alias("student_mismatch"),
            (
                (pl.col("teacher_race_mismatch") + pl.col("teacher_hisp_mismatch")) / 2.0
            ).alias("teacher_mismatch"),
        ]
    )

    # Cleanup and filtering
    analysis_df = model_df.filter(
        pl.col("ach_all").is_not_null()
        & pl.col("student_mismatch").is_not_null()
        & pl.col("teacher_mismatch").is_not_null()
    )

    # Quintiles using qcut
    analysis_df = analysis_df.with_columns(
        [
            pl.col("student_mismatch")
            .qcut(5, labels=[f"Q{i}" for i in range(1, 6)], allow_duplicates=True)
            .alias("student_mismatch_q"),
            pl.col("teacher_mismatch")
            .qcut(5, labels=[f"Q{i}" for i in range(1, 6)], allow_duplicates=True)
            .alias("teacher_mismatch_q"),
        ]
    )
    return (analysis_df,)


@app.cell(hide_code=True)
def _(analysis_df, pl):
    coverage = {
        "n_schools_used": int(analysis_df["school_key"].n_unique()),
        "n_rows_used": int(len(analysis_df)),
        "n_with_county_link": int(
            analysis_df.filter(pl.col("county_fips").is_not_null()).height
        ),
        "n_missing_county_link": int(
            analysis_df.filter(pl.col("county_fips").is_null()).height
        ),
        "achievement_mean": float(analysis_df["ach_all"].mean()),
    }
    return


@app.cell
def _(analysis_df, np, plt):
    def scatter_with_fit(ax, x, y, x_label, y_label, title):
        ax.scatter(x, y, alpha=0.5, s=20)
        if len(x) >= 3:
            coeff = np.polyfit(x, y, deg=1)
            xs = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 100)
            ys = coeff[0] * xs + coeff[1]
            ax.plot(xs, ys, color="tab:red", linewidth=2)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(title)
        ax.grid(alpha=0.25)

    _x = analysis_df["student_mismatch"].to_numpy()
    _y = analysis_df["ach_all"].to_numpy()
    _tx = analysis_df["teacher_mismatch"].to_numpy()

    _fig_scatter, _axes_scatter = plt.subplots(2, 2, figsize=(14, 10))
    scatter_with_fit(
        _axes_scatter[0, 0],
        _x,
        _y,
        "Student-area mismatch",
        "Achievement (ach_all)",
        "Achievement vs Student-Area Mismatch",
    )
    scatter_with_fit(
        _axes_scatter[0, 1],
        _tx,
        _y,
        "Teacher-area mismatch",
        "Achievement (ach_all)",
        "Achievement vs Teacher-Area Mismatch",
    )

    colors = _y
    _sc = _axes_scatter[1, 0].scatter(
        _x,
        _tx,
        c=colors,
        cmap="viridis",
        alpha=0.6,
        s=24,
    )
    _axes_scatter[1, 0].set_xlabel("Student-area mismatch")
    _axes_scatter[1, 0].set_ylabel("Teacher-area mismatch")
    _axes_scatter[1, 0].set_title("Student vs Teacher Mismatch (color = achievement)")
    _axes_scatter[1, 0].grid(alpha=0.25)
    _fig_scatter.colorbar(_sc, ax=_axes_scatter[1, 0], label="ach_all")

    _axes_scatter[1, 1].hist(_x, bins=20, alpha=0.6, label="student mismatch")
    _axes_scatter[1, 1].hist(_tx, bins=20, alpha=0.6, label="teacher mismatch")
    _axes_scatter[1, 1].set_xlabel("Mismatch score")
    _axes_scatter[1, 1].set_ylabel("Count")
    _axes_scatter[1, 1].set_title("Mismatch Distributions")
    _axes_scatter[1, 1].legend()
    _axes_scatter[1, 1].grid(alpha=0.25)

    _fig_scatter.tight_layout()
    _fig_scatter
    return


@app.cell
def _(analysis_df, district_top_n, pl, plt):
    _fig_box, _axes_box = plt.subplots(1, 3, figsize=(18, 5))

    quintiles = ["Q1", "Q2", "Q3", "Q4", "Q5"]
    student_groups = [
        analysis_df.filter(pl.col("student_mismatch_q") == q)["ach_all"].to_numpy()
        for q in quintiles
        if q in analysis_df["student_mismatch_q"].unique().to_list()
    ]
    teacher_groups = [
        analysis_df.filter(pl.col("teacher_mismatch_q") == q)["ach_all"].to_numpy()
        for q in quintiles
        if q in analysis_df["teacher_mismatch_q"].unique().to_list()
    ]

    if student_groups:
        _axes_box[0].boxplot(student_groups, patch_artist=True)
        _axes_box[0].set_xticklabels(quintiles[: len(student_groups)])
    _axes_box[0].set_title("Achievement by Student Mismatch Quintile")
    _axes_box[0].set_xlabel("Mismatch quintile")
    _axes_box[0].set_ylabel("ach_all")
    _axes_box[0].grid(alpha=0.25)

    if teacher_groups:
        _axes_box[1].boxplot(teacher_groups, patch_artist=True)
        _axes_box[1].set_xticklabels(quintiles[: len(teacher_groups)])
    _axes_box[1].set_title("Achievement by Teacher Mismatch Quintile")
    _axes_box[1].set_xlabel("Mismatch quintile")
    _axes_box[1].set_ylabel("ach_all")
    _axes_box[1].grid(alpha=0.25)

    district_counts = (
        analysis_df.group_by("district_name")
        .count()
        .sort("count", descending=True)
        .head(district_top_n.value)
    )
    district_order = district_counts["district_name"].to_list()

    district_box_data = [
        analysis_df.filter(pl.col("district_name") == d)["ach_all"].to_numpy()
        for d in district_order
    ]
    if district_box_data:
        _axes_box[2].boxplot(district_box_data, patch_artist=True)
        _axes_box[2].set_xticklabels(district_order, rotation=90)
    _axes_box[2].set_title(f"Achievement by Top {district_top_n.value} Districts")
    _axes_box[2].set_xlabel("District")
    _axes_box[2].set_ylabel("ach_all")
    _axes_box[2].grid(alpha=0.25)

    _fig_box.tight_layout()
    _fig_box
    return


@app.cell
def _(analysis_df, min_test_n, pl, stats):
    test_rows = []

    def add_result(
        test_name: str,
        statistic: float | None,
        p_value: float | None,
        n_used: int,
        detail: str,
    ):
        if p_value is None:
            interpretation = "insufficient data"
        elif p_value < 0.001:
            interpretation = "very strong evidence"
        elif p_value < 0.01:
            interpretation = "strong evidence"
        elif p_value < 0.05:
            interpretation = "moderate evidence"
        else:
            interpretation = "weak/no evidence"
        test_rows.append(
            {
                "test": test_name,
                "statistic": statistic,
                "p_value": p_value,
                "n_used": n_used,
                "interpretation": interpretation,
                "detail": detail,
            }
        )

    # Student mismatch vs achievement
    _student_m = analysis_df["student_mismatch"].to_numpy()
    _ach = analysis_df["ach_all"].to_numpy()
    if len(_student_m) >= min_test_n.value:
        pear = stats.pearsonr(_student_m, _ach)
        spear = stats.spearmanr(_student_m, _ach)
        add_result(
            "Pearson: student mismatch vs achievement",
            float(pear.statistic),
            float(pear.pvalue),
            len(_student_m),
            "linear association",
        )
        add_result(
            "Spearman: student mismatch vs achievement",
            float(spear.statistic),
            float(spear.pvalue),
            len(_student_m),
            "rank association",
        )
    else:
        add_result(
            "Pearson: student mismatch vs achievement",
            None,
            None,
            len(_student_m),
            "linear association",
        )
        add_result(
            "Spearman: student mismatch vs achievement",
            None,
            None,
            len(_student_m),
            "rank association",
        )

    # Teacher mismatch vs achievement
    _teacher_m = analysis_df["teacher_mismatch"].to_numpy()
    if len(_teacher_m) >= min_test_n.value:
        pear = stats.pearsonr(_teacher_m, _ach)
        spear = stats.spearmanr(_teacher_m, _ach)
        add_result(
            "Pearson: teacher mismatch vs achievement",
            float(pear.statistic),
            float(pear.pvalue),
            len(_teacher_m),
            "linear association",
        )
        add_result(
            "Spearman: teacher mismatch vs achievement",
            float(spear.statistic),
            float(spear.pvalue),
            len(_teacher_m),
            "rank association",
        )
    else:
        add_result(
            "Pearson: teacher mismatch vs achievement",
            None,
            None,
            len(_teacher_m),
            "linear association",
        )
        add_result(
            "Spearman: teacher mismatch vs achievement",
            None,
            None,
            len(_teacher_m),
            "rank association",
        )

    # Quintile contrasts
    def get_q_data(col, q):
        return analysis_df.filter(pl.col(col) == q)["ach_all"].to_numpy()

    student_q1 = get_q_data("student_mismatch_q", "Q1")
    student_q5 = get_q_data("student_mismatch_q", "Q5")
    if len(student_q1) >= min_test_n.value and len(student_q5) >= min_test_n.value:
        t_res = stats.ttest_ind(student_q1, student_q5, equal_var=False)
        add_result(
            "Welch t-test: student mismatch Q1 vs Q5",
            float(t_res.statistic),
            float(t_res.pvalue),
            len(student_q1) + len(student_q5),
            "mean achievement contrast",
        )
    else:
        add_result(
            "Welch t-test: student mismatch Q1 vs Q5",
            None,
            None,
            len(student_q1) + len(student_q5),
            "mean achievement contrast",
        )

    teacher_q1 = get_q_data("teacher_mismatch_q", "Q1")
    teacher_q5 = get_q_data("teacher_mismatch_q", "Q5")
    if len(teacher_q1) >= min_test_n.value and len(teacher_q5) >= min_test_n.value:
        t_res = stats.ttest_ind(teacher_q1, teacher_q5, equal_var=False)
        add_result(
            "Welch t-test: teacher mismatch Q1 vs Q5",
            float(t_res.statistic),
            float(t_res.pvalue),
            len(teacher_q1) + len(teacher_q5),
            "mean achievement contrast",
        )
    else:
        add_result(
            "Welch t-test: teacher mismatch Q1 vs Q5",
            None,
            None,
            len(teacher_q1) + len(teacher_q5),
            "mean achievement contrast",
        )

    # ANOVA
    def run_anova(col):
        groups = [
            analysis_df.filter(pl.col(col) == q)["ach_all"].to_numpy()
            for q in ["Q1", "Q2", "Q3", "Q4", "Q5"]
        ]
        groups = [g for g in groups if len(g) >= min_test_n.value]
        if len(groups) >= 3:
            res = stats.f_oneway(*groups)
            return float(res.statistic), float(res.pvalue), sum(len(g) for g in groups)
        return None, None, sum(len(g) for g in groups)

    stat, pval, n = run_anova("student_mismatch_q")
    add_result(
        "ANOVA: achievement across student mismatch quintiles",
        stat,
        pval,
        n,
        "multi-group mean difference",
    )

    stat, pval, n = run_anova("teacher_mismatch_q")
    add_result(
        "ANOVA: achievement across teacher mismatch quintiles",
        stat,
        pval,
        n,
        "multi-group mean difference",
    )

    # Chi-square (requires bucketing achievement)
    if len(analysis_df) >= min_test_n.value:
        ach_q = analysis_df["ach_all"].qcut(3, labels=["low", "mid", "high"])
        # Polars doesn't have crosstab in the same way, but we can do a group_by and pivot
        temp = analysis_df.with_columns(ach_bucket=ach_q)
        ct = (
            temp.group_by(["student_mismatch_q", "ach_bucket"])
            .count()
            .pivot(on="ach_bucket", index="student_mismatch_q", values="count")
            .fill_null(0)
        )

        # Convert to numpy for chi2
        obs = ct.select(["low", "mid", "high"]).to_numpy()
        if obs.shape[0] >= 2 and obs.shape[1] >= 2:
            chi2, p_val, _, _ = stats.chi2_contingency(obs)
            add_result(
                "Chi-square: student mismatch quintile vs achievement tertile",
                float(chi2),
                float(p_val),
                int(obs.sum()),
                "categorical association",
            )
        else:
            add_result(
                "Chi-square: student mismatch quintile vs achievement tertile",
                None,
                None,
                len(analysis_df),
                "categorical association",
            )
    else:
        add_result(
            "Chi-square: student mismatch quintile vs achievement tertile",
            None,
            None,
            len(analysis_df),
            "categorical association",
        )

    test_results_df = pl.DataFrame(test_rows).with_columns(
        [
            pl.col("statistic").round(4),
            pl.col("p_value").round(6),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    preview_cols = [
        "school_key",
        "district_name",
        "locale_type",
        "ach_all",
        "student_mismatch",
        "teacher_mismatch",
        "student_mismatch_q",
        "teacher_mismatch_q",
    ]
    return


@app.cell
def _(run_query, year_selector):
    _joined_query = """
    WITH base AS (
      SELECT
        school_key,
        year,
        school_year_label,
        state_code,
        department_name,
        district_name,
        school_name,
        state_school_id,
        nces_id,
        nces_geo_id,
        census_id,
        nces_charter,
        nces_magnet,
        county_fips,
        county_name
      FROM core.vw_school_year_geo_context
    ),
    student AS (
      SELECT
        school_key,
        year,
        total_student_count,
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
        total_staff_count,
        teacher_support_staff_pct,
        teacher_diversity_index,
        teacher_diversity_chance_pct,
        teacher_prevalence_1st_pct,
        teacher_prevalence_2nd_pct,
        teacher_prevalence_3rd_pct,
        teacher_diffusion_score_pct
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
        effectiveness_score AS teacher_effectiveness_score,
        atot_completion_rate_designation,
        title_i_status AS teacher_eff_title_i_status
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
    edunomics AS (
      SELECT
        school_key,
        year,
        ncesenroll,
        gradespan,
        level,
        enroll_raw,
        state_local_per_pupil,
        state_local_fund,
        nces_fund,
        nces_poverty,
        title_i_status,
        nces_charter,
        nces_magnet,
        nces_freelunch,
        nces_reducedlunch,
        per_pupil_nces_raw,
        per_pupil_total_raw,
        flag_nerds,
        flag_f33
      FROM core.fact_edunomics
    ),
    area_pop AS (
      SELECT
        county_fips,
        year,
        MAX(population_count) FILTER (WHERE population_group = 'total') AS county_pop_total,
        MAX(population_count) FILTER (WHERE population_group = 'hisp') AS county_pop_hisp,
        MAX(population_count) FILTER (WHERE population_group = 'white') AS county_pop_white,
        MAX(population_count) FILTER (WHERE population_group = 'black') AS county_pop_black,
        MAX(population_count) FILTER (WHERE population_group = 'asian') AS county_pop_asian
      FROM core.fact_geo_population_county
      GROUP BY county_fips, year
    ),
    area_opp AS (
      SELECT
        county_fips,
        year,
        MAX(opportunity_score_avg) FILTER (WHERE metric_code = 'COI' AND norm_scope = 'stt') AS county_coi_score_stt,
        MAX(opportunity_zscore_avg) FILTER (WHERE metric_code = 'COI' AND norm_scope = 'stt') AS county_coi_z_stt,
        MAX(opportunity_score_avg) FILTER (WHERE metric_code = 'COI' AND norm_scope = 'met') AS county_coi_score_met,
        MAX(opportunity_zscore_avg) FILTER (WHERE metric_code = 'COI' AND norm_scope = 'met') AS county_coi_z_met
      FROM core.fact_geo_opportunity_county
      GROUP BY county_fips, year
    )
    SELECT
      b.*,
      st.total_student_count,
      st.student_diversity_index,
      st.student_prevalence_1st_pct,
      st.student_prevalence_2nd_pct,
      st.student_prevalence_3rd_pct,
      st.student_diffusion_score_pct,
      sf.total_staff_count,
      sf.teacher_support_staff_pct,
      sf.teacher_diversity_index,
      sf.teacher_diversity_chance_pct,
      sf.teacher_prevalence_1st_pct,
      sf.teacher_prevalence_2nd_pct,
      sf.teacher_prevalence_3rd_pct,
      sf.teacher_diffusion_score_pct,
      te.principal_exp_pct,
      te.principal_inexp_pct,
      te.teacher_exp_pct,
      te.teacher_inexp_pct,
      te.leader_exp_pct,
      te.leader_inexp_pct,
      tf.teacher_effectiveness_score,
      tf.atot_completion_rate_designation,
      tf.teacher_eff_title_i_status,
      so.ach_all,
      so.grw_all,
      so.abs_all,
      so.coi,
      so.coi_ed,
      so.coi_he,
      so.coi_st,
      so.ppe,
      edu.ncesenroll,
      edu.gradespan,
      edu.level,
      edu.enroll_raw,
      edu.state_local_per_pupil,
      edu.state_local_fund,
      edu.nces_fund,
      edu.nces_poverty,
      edu.title_i_status,
      edu.nces_freelunch,
      edu.nces_reducedlunch,
      edu.per_pupil_nces_raw,
      edu.per_pupil_total_raw,
      edu.flag_nerds,
      edu.flag_f33,
      ap.county_pop_total,
      ap.county_pop_hisp,
      ap.county_pop_white,
      ap.county_pop_black,
      ap.county_pop_asian,
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
    LEFT JOIN edunomics edu USING (school_key, year)
    LEFT JOIN area_pop ap
      ON ap.county_fips = b.county_fips
     AND ap.year = b.year
    LEFT JOIN area_opp ao
      ON ao.county_fips = b.county_fips
     AND ao.year = b.year
    WHERE b.year = %s
    """

    raw_year_df = run_query(_joined_query, (year_selector.value,))
    raw_funding_df = run_query(_joined_query, (2022,))
    return raw_funding_df, raw_year_df


@app.cell(hide_code=True)
def _(mo, year_selector):
    mo.md(f"""
    ### Metric Scatterplots

    - Achievement-linked plots use selected year: **{year_selector.value}**
    - Funding-linked plots use fallback year: **2022** (`fact_edunomics` latest year)
    - `teacher_effectiveness_score` excludes `Missing Data` and `No Data`
    """)
    return


@app.cell
def _(np, pl, raw_funding_df, raw_year_df):
    _numeric_cols = [
        "ach_all",
        "student_diversity_index",
        "teacher_diversity_index",
        "teacher_exp_pct",
        "coi",
        "per_pupil_total_raw",
    ]

    def _prep_frame(_df):
        _clean = _df.with_columns(
            pl.when(
                pl.col("teacher_effectiveness_score").is_in(
                    ["Missing Data", "No Data", ""]
                )
            )
            .then(None)
            .otherwise(pl.col("teacher_effectiveness_score"))
            .alias("teacher_effectiveness_score")
        )
        _clean = _clean.with_columns(
            [
                pl.col(c).cast(pl.Float64, strict=False).alias(c)
                for c in _numeric_cols + ["teacher_effectiveness_score"]
                if c in _clean.columns
            ]
        )
        _clean = _clean.with_columns(
            pl.col("per_pupil_total_raw")
            .map_elements(np.log1p, return_dtype=pl.Float64)
            .alias("per_pupil_total_k")
        )
        _clean = _clean.with_columns(
            (
                (pl.col("per_pupil_total_k") - pl.col("per_pupil_total_k").mean())
                / pl.col("per_pupil_total_k").std()
            ).alias("per_pupil_total_k")
        )
        return _clean

    year_metrics_df = _prep_frame(raw_year_df)
    funding_metrics_df = _prep_frame(raw_funding_df)
    return funding_metrics_df, year_metrics_df


@app.cell
def _(funding_metrics_df, np, plt, year_metrics_df):
    def _scatter_and_fit(_ax, _x, _y, _xlabel, _ylabel, _title):
        _ax.scatter(_x, _y, alpha=0.45, s=18)
        if len(_x) >= 3:
            _coef = np.polyfit(_x, _y, deg=1)
            _xs = np.linspace(float(np.min(_x)), float(np.max(_x)), 120)
            _ax.plot(_xs, _coef[0] * _xs + _coef[1], color="tab:red", linewidth=1.8)
        _ax.set_xlabel(_xlabel)
        _ax.set_ylabel(_ylabel)
        _ax.set_title(_title)
        _ax.grid(alpha=0.25)

    def _xy(_df, _xcol, _ycol):
        _s = _df.select([_xcol, _ycol]).drop_nulls()
        return _s[_xcol].to_numpy(), _s[_ycol].to_numpy()

    _fig_targets, _axes_targets = plt.subplots(6, 2, figsize=(14, 24))

    _pairs = [
        ("student_diversity_index", "Student Diversity Index"),
        ("teacher_diversity_index", "Teacher Diversity Index"),
        ("teacher_exp_pct", "Teacher Exp Pct"),
        ("teacher_effectiveness_score", "Teacher Effectiveness Score"),
        ("coi", "COI"),
    ]

    _x, _y = _xy(year_metrics_df, "student_diversity_index", "ach_all")
    _scatter_and_fit(
        _axes_targets[0, 0],
        _x,
        _y,
        "student_diversity_index",
        "ach_all",
        "Achievement vs Student Diversity Index",
    )
    _x, _y = _xy(funding_metrics_df, "student_diversity_index", "per_pupil_total_k")
    _scatter_and_fit(
        _axes_targets[0, 1],
        _x,
        _y,
        "student_diversity_index",
        "per_pupil_total_k",
        "Funding vs Student Diversity Index",
    )

    _x, _y = _xy(year_metrics_df, "teacher_diversity_index", "ach_all")
    _scatter_and_fit(
        _axes_targets[1, 0],
        _x,
        _y,
        "teacher_diversity_index",
        "ach_all",
        "Achievement vs Teacher Diversity Index",
    )
    _x, _y = _xy(funding_metrics_df, "teacher_diversity_index", "per_pupil_total_k")
    _scatter_and_fit(
        _axes_targets[1, 1],
        _x,
        _y,
        "teacher_diversity_index",
        "per_pupil_total_k",
        "Funding vs Teacher Diversity Index",
    )

    _x, _y = _xy(year_metrics_df, "student_diversity_index", "teacher_diversity_index")
    _scatter_and_fit(
        _axes_targets[2, 0],
        _x,
        _y,
        "student_diversity_index",
        "teacher_diversity_index",
        "Student Diversity vs Teacher Diversity",
    )
    _x, _y = _xy(funding_metrics_df, "student_diversity_index", "teacher_diversity_index")
    _scatter_and_fit(
        _axes_targets[2, 1],
        _x,
        _y,
        "student_diversity_index",
        "teacher_diversity_index",
        "Student Diversity vs Teacher Diversity (2022)",
    )

    _x, _y = _xy(year_metrics_df, "teacher_exp_pct", "ach_all")
    _scatter_and_fit(
        _axes_targets[3, 0],
        _x,
        _y,
        "teacher_exp_pct",
        "ach_all",
        "Achievement vs Teacher Exp Pct",
    )
    _x, _y = _xy(funding_metrics_df, "teacher_exp_pct", "per_pupil_total_k")
    _scatter_and_fit(
        _axes_targets[3, 1],
        _x,
        _y,
        "teacher_exp_pct",
        "per_pupil_total_k",
        "Funding vs Teacher Exp Pct",
    )

    _x, _y = _xy(year_metrics_df, "teacher_effectiveness_score", "ach_all")
    _scatter_and_fit(
        _axes_targets[4, 0],
        _x,
        _y,
        "teacher_effectiveness_score",
        "ach_all",
        "Achievement vs Teacher Effectiveness",
    )
    _x, _y = _xy(funding_metrics_df, "teacher_effectiveness_score", "per_pupil_total_k")
    _scatter_and_fit(
        _axes_targets[4, 1],
        _x,
        _y,
        "teacher_effectiveness_score",
        "per_pupil_total_k",
        "Funding vs Teacher Effectiveness",
    )

    _x, _y = _xy(year_metrics_df, "coi", "ach_all")
    _scatter_and_fit(
        _axes_targets[5, 0],
        _x,
        _y,
        "coi",
        "ach_all",
        "Achievement vs COI",
    )
    _x, _y = _xy(funding_metrics_df, "coi", "per_pupil_total_k")
    _scatter_and_fit(
        _axes_targets[5, 1],
        _x,
        _y,
        "coi",
        "per_pupil_total_k",
        "Funding vs COI",
    )

    _fig_targets.tight_layout()
    _fig_targets
    return


@app.cell(hide_code=True)
def _(funding_metrics_df, min_test_n, mo, pl, stats, year_metrics_df):
    def _interp(_p):
        if _p is None:
            return "insufficient data"
        if _p < 0.001:
            return "very strong evidence"
        if _p < 0.01:
            return "strong evidence"
        if _p < 0.05:
            return "moderate evidence"
        return "weak/no evidence"

    _rows = []
    _metric_specs = [
        "student_diversity_index",
        "teacher_diversity_index",
        "teacher_exp_pct",
        "teacher_effectiveness_score",
        "coi",
    ]

    def _add_corrs(_df, _target, _label):
        for _metric in _metric_specs:
            _s = _df.select([_metric, _target]).drop_nulls()
            _n = _s.height
            if _n >= min_test_n.value:
                _x = _s[_metric].to_numpy()
                _y = _s[_target].to_numpy()
                _p = stats.pearsonr(_x, _y)
                _sp = stats.spearmanr(_x, _y)
                _rows.append(
                    {
                        "domain": _label,
                        "test": "pearsonr",
                        "metric": _metric,
                        "target": _target,
                        "statistic": float(_p.statistic),
                        "p_value": float(_p.pvalue),
                        "n": _n,
                        "interpretation": _interp(float(_p.pvalue)),
                    }
                )
                _rows.append(
                    {
                        "domain": _label,
                        "test": "spearmanr",
                        "metric": _metric,
                        "target": _target,
                        "statistic": float(_sp.statistic),
                        "p_value": float(_sp.pvalue),
                        "n": _n,
                        "interpretation": _interp(float(_sp.pvalue)),
                    }
                )
            else:
                _rows.append(
                    {
                        "domain": _label,
                        "test": "pearsonr",
                        "metric": _metric,
                        "target": _target,
                        "statistic": None,
                        "p_value": None,
                        "n": _n,
                        "interpretation": "insufficient data",
                    }
                )
                _rows.append(
                    {
                        "domain": _label,
                        "test": "spearmanr",
                        "metric": _metric,
                        "target": _target,
                        "statistic": None,
                        "p_value": None,
                        "n": _n,
                        "interpretation": "insufficient data",
                    }
                )

    _add_corrs(year_metrics_df, "ach_all", "selected-year")
    _add_corrs(funding_metrics_df, "per_pupil_total_k", "funding-2022")

    _tests_df = pl.DataFrame(_rows).with_columns(
        [pl.col("statistic").round(4), pl.col("p_value").round(6)]
    )
    mo.vstack([mo.md("### Scatterplot Hypothesis Tests"), mo.ui.table(_tests_df)])
    return


if __name__ == "__main__":
    app.run()
