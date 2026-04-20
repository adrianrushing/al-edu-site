from __future__ import annotations

import os
from datetime import datetime

import polars as pl
import psycopg

DEFAULT_DB_URI = "postgresql://localhost:5433/eflt"


def db_uri() -> str:
    return os.getenv("DATABASE_URL") or os.getenv("DB_URI") or DEFAULT_DB_URI


def read_df(conn: psycopg.Connection, query: str) -> pl.DataFrame:
    return pl.read_database(query=query, connection=conn)


def normalize_text_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .cast(pl.String)
        .str.strip_chars()
        .str.replace_all(r"[[:space:]]+", " ")
    )


def parse_last_int_expr(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .cast(pl.String)
        .str.strip_chars()
        .str.extract(r"(\d+)$", 1)
        .cast(pl.Int64, strict=False)
    )


def parse_bool_expr(col: str) -> pl.Expr:
    cleaned = (
        pl.col(col)
        .cast(pl.String)
        .str.strip_chars()
        .str.to_lowercase()
        .str.replace(r"^\d+\s*-\s*", "", literal=False)
    )
    return (
        pl.when(cleaned.is_in(["yes", "y", "true", "t", "1"]))
        .then(pl.lit(True))
        .when(cleaned.is_in(["no", "n", "false", "f", "0"]))
        .then(pl.lit(False))
        .otherwise(pl.lit(None, dtype=pl.Boolean))
    )


def year_start_expr() -> pl.Expr:
    return (
        pl.when(pl.col("year").str.contains(r"^\d{4}-\d{4}$"))
        .then(pl.col("year").str.slice(0, 4).cast(pl.Int64, strict=False))
        .when(pl.col("year").str.contains(r"^\d{4}$"))
        .then(pl.col("year").cast(pl.Int64, strict=False))
        .otherwise(None)
    )


def year_end_expr() -> pl.Expr:
    return (
        pl.when(pl.col("year").str.contains(r"^\d{4}-\d{4}$"))
        .then(pl.col("year").str.slice(5, 4).cast(pl.Int64, strict=False))
        .when(pl.col("year").str.contains(r"^\d{4}$"))
        .then(pl.col("year").cast(pl.Int64, strict=False) + 1)
        .otherwise(None)
    )


def school_year_label_expr() -> pl.Expr:
    return (
        pl.when(pl.col("year").str.contains(r"^\d{4}-\d{4}$"))
        .then(pl.col("year"))
        .when(pl.col("year").str.contains(r"^\d{4}$"))
        .then(
            pl.concat_str(
                [
                    pl.col("year"),
                    pl.lit("-"),
                    (pl.col("year").cast(pl.Int64, strict=False) + 1).cast(pl.String),
                ]
            )
        )
        .otherwise(None)
    )


def locale_code_expr() -> pl.Expr:
    locale = pl.col("nces_locale").cast(pl.String).str.strip_chars()
    locale_l = locale.str.to_lowercase()
    return (
        pl.when(locale.str.contains(r"^\d{2}-"))
        .then(locale.str.extract(r"^(\d{2})", 1).cast(pl.Int64, strict=False))
        .when(locale_l.is_in(["city: midsize", "city: mid-size"]))
        .then(pl.lit(12))
        .when(locale_l == "city: small")
        .then(pl.lit(13))
        .when(locale_l == "suburb: large")
        .then(pl.lit(21))
        .when(locale_l.is_in(["suburb: midsize", "suburb: mid-size"]))
        .then(pl.lit(22))
        .when(locale_l == "suburb: small")
        .then(pl.lit(23))
        .when(locale_l == "town: fringe")
        .then(pl.lit(31))
        .when(locale_l == "town: distant")
        .then(pl.lit(32))
        .when(locale_l == "town: remote")
        .then(pl.lit(33))
        .when(locale_l == "rural: fringe")
        .then(pl.lit(41))
        .when(locale_l == "rural: distant")
        .then(pl.lit(42))
        .when(locale_l == "rural: remote")
        .then(pl.lit(43))
        .otherwise(None)
    )


def classify_row_expr() -> pl.Expr:
    dist_norm = pl.col("dist_name_norm")
    school_norm = pl.col("school_name_norm")
    return (
        pl.when(
            (dist_norm == school_norm)
            & dist_norm.str.contains("state department of education")
        )
        .then(pl.lit("STATE"))
        .when(dist_norm == school_norm)
        .then(pl.lit("DISTRICT"))
        .otherwise(pl.lit("SCHOOL"))
    )


def build_school_rows(conn: psycopg.Connection) -> pl.DataFrame:
    locale_ref = read_df(
        conn,
        """
        SELECT locale_code, nces_locale_key, locale_group, locale_subtype, is_unknown
        FROM ref.nces_locale_canonical;
        """,
    )
    unknown = locale_ref.filter(pl.col("is_unknown")).head(1)
    if unknown.height == 0:
        raise RuntimeError("ref.nces_locale_canonical missing is_unknown row")
    unknown_key = int(unknown["nces_locale_key"][0])
    unknown_group = str(unknown["locale_group"][0])
    unknown_subtype = str(unknown["locale_subtype"][0])

    edu = read_df(
        conn,
        """
        SELECT
            state,
            year,
            distid_stateassigned,
            schoolid_stateassigned,
            distname,
            schoolname,
            ncesdistid_admin,
            ncesdistid_geo,
            census_id,
            ncesid,
            nces_locale,
            nces_charter,
            nces_magnet,
            nces_address,
            nces_city,
            nces_zip,
            _source_file,
            _ingested_at
        FROM staging.stg_school_edunomics;
        """,
    )

    edu_rows = (
        edu.with_columns(
            [
                pl.lit("AL").alias("state_code"),
                school_year_label_expr().alias("school_year_label"),
                year_start_expr().alias("school_year_start"),
                year_end_expr().alias("school_year_end"),
                normalize_text_expr("distname").alias("dist_name"),
                normalize_text_expr("schoolname").alias("school_name"),
                normalize_text_expr("distname")
                .str.to_lowercase()
                .alias("dist_name_norm"),
                normalize_text_expr("schoolname")
                .str.to_lowercase()
                .alias("school_name_norm"),
                parse_last_int_expr("distid_stateassigned").alias("state_dist_id"),
                parse_last_int_expr("schoolid_stateassigned").alias("state_school_id"),
                parse_last_int_expr("ncesdistid_admin").alias("nces_admin_id"),
                parse_last_int_expr("ncesdistid_geo").alias("nces_geo_id"),
                parse_last_int_expr("census_id").alias("census_id"),
                parse_last_int_expr("ncesid").alias("nces_id"),
                locale_code_expr().alias("locale_code"),
                parse_bool_expr("nces_charter").alias("nces_charter_bool"),
                parse_bool_expr("nces_magnet").alias("nces_magnet_bool"),
                normalize_text_expr("nces_address").alias("nces_address_clean"),
                normalize_text_expr("nces_city").alias("nces_city_clean"),
                pl.col("nces_zip")
                .cast(pl.String)
                .str.strip_chars()
                .alias("nces_zip_clean"),
                pl.lit(0).alias("source_priority"),
            ]
        )
        .filter(
            pl.col("school_year_start").is_not_null()
            & pl.col("dist_name").is_not_null()
            & pl.col("school_name").is_not_null()
            & (pl.col("dist_name") != "")
            & (pl.col("school_name") != "")
        )
        .with_columns(classify_row_expr().alias("row_type"))
    )

    locale_lookup = locale_ref.select(
        [
            pl.col("locale_code").cast(pl.Int64).alias("locale_code"),
            pl.col("nces_locale_key").cast(pl.Int64),
            pl.col("locale_group").alias("nces_locale_type"),
            pl.col("locale_subtype").alias("nces_locale_subtype"),
        ]
    )

    edu_rows = (
        edu_rows.join(locale_lookup, on="locale_code", how="left")
        .with_columns(
            [
                pl.col("nces_locale_key").fill_null(unknown_key),
                pl.col("nces_locale_type").fill_null(unknown_group),
                pl.col("nces_locale_subtype").fill_null(unknown_subtype),
                pl.col("nces_charter_bool").alias("nces_charter"),
                pl.col("nces_magnet_bool").alias("nces_magnet"),
            ]
        )
        .select(
            [
                "state_code",
                "school_year_label",
                "school_year_start",
                "school_year_end",
                "dist_name",
                "school_name",
                "dist_name_norm",
                "school_name_norm",
                "row_type",
                "state_dist_id",
                "state_school_id",
                "nces_admin_id",
                "nces_geo_id",
                "census_id",
                "nces_id",
                "nces_locale_key",
                "nces_locale_type",
                "nces_locale_subtype",
                "nces_charter",
                "nces_magnet",
                pl.col("nces_address_clean").alias("nces_address"),
                pl.col("nces_city_clean").alias("nces_city"),
                pl.col("nces_zip_clean").alias("nces_zip"),
                pl.col("nces_locale").cast(pl.String).alias("source_nces_locale"),
                pl.col("distid_stateassigned")
                .cast(pl.String)
                .alias("source_state_dist_id"),
                pl.col("schoolid_stateassigned")
                .cast(pl.String)
                .alias("source_state_school_id"),
                pl.col("_source_file").cast(pl.String),
                pl.col("_ingested_at").cast(pl.Datetime("us")),
                "source_priority",
            ]
        )
    )

    # Fallback rows only for missing school-year coverage.
    try:
        fallback = read_df(
            conn,
            """
            SELECT DISTINCT year, system, school
            FROM sandbox.impute_teacher_demographics;
            """,
        )
    except Exception:
        fallback = pl.DataFrame({"year": [], "system": [], "school": []})

    if fallback.height > 0:
        fallback_rows = (
            fallback.with_columns(
                [
                    pl.lit("AL").alias("state_code"),
                    pl.col("year")
                    .cast(pl.Int64, strict=False)
                    .alias("school_year_start"),
                    (pl.col("year").cast(pl.Int64, strict=False) + 1).alias(
                        "school_year_end"
                    ),
                    pl.concat_str(
                        [
                            pl.col("year").cast(pl.Int64, strict=False).cast(pl.String),
                            pl.lit("-"),
                            (pl.col("year").cast(pl.Int64, strict=False) + 1).cast(
                                pl.String
                            ),
                        ]
                    ).alias("school_year_label"),
                    normalize_text_expr("system").alias("dist_name"),
                    normalize_text_expr("school").alias("school_name"),
                    normalize_text_expr("system")
                    .str.to_lowercase()
                    .alias("dist_name_norm"),
                    normalize_text_expr("school")
                    .str.to_lowercase()
                    .alias("school_name_norm"),
                ]
            )
            .with_columns(
                [
                    classify_row_expr().alias("row_type"),
                    pl.lit(None, dtype=pl.Int64).alias("state_dist_id"),
                    pl.lit(None, dtype=pl.Int64).alias("state_school_id"),
                    pl.lit(None, dtype=pl.Int64).alias("nces_admin_id"),
                    pl.lit(None, dtype=pl.Int64).alias("nces_geo_id"),
                    pl.lit(None, dtype=pl.Int64).alias("census_id"),
                    pl.lit(None, dtype=pl.Int64).alias("nces_id"),
                    pl.lit(unknown_key).alias("nces_locale_key"),
                    pl.lit(unknown_group).alias("nces_locale_type"),
                    pl.lit(unknown_subtype).alias("nces_locale_subtype"),
                    pl.lit(None, dtype=pl.Boolean).alias("nces_charter"),
                    pl.lit(None, dtype=pl.Boolean).alias("nces_magnet"),
                    pl.lit(None, dtype=pl.String).alias("nces_address"),
                    pl.lit(None, dtype=pl.String).alias("nces_city"),
                    pl.lit(None, dtype=pl.String).alias("nces_zip"),
                    pl.lit(None, dtype=pl.String).alias("source_nces_locale"),
                    pl.lit(None, dtype=pl.String).alias("source_state_dist_id"),
                    pl.lit(None, dtype=pl.String).alias("source_state_school_id"),
                    pl.lit("impute_teacher_demographics").alias("_source_file"),
                    pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_ingested_at"),
                    pl.lit(1).alias("source_priority"),
                ]
            )
            .select(edu_rows.columns)
        )

        existing_keys = edu_rows.select(
            ["school_year_start", "dist_name_norm", "school_name_norm"]
        )
        fallback_missing = fallback_rows.join(
            existing_keys,
            on=["school_year_start", "dist_name_norm", "school_name_norm"],
            how="anti",
        )
        combined = pl.concat([edu_rows, fallback_missing], how="vertical_relaxed")
    else:
        combined = edu_rows

    # Deduplicate by school-year + normalized names with deterministic preference.
    prepared = combined.sort(
        by=[
            "school_year_start",
            "dist_name_norm",
            "school_name_norm",
            "source_priority",
            "state_school_id",
            "nces_id",
            "_ingested_at",
            "_source_file",
        ],
        descending=[False, False, False, False, True, True, True, False],
        nulls_last=True,
    ).unique(
        subset=["school_year_start", "dist_name_norm", "school_name_norm"],
        keep="first",
        maintain_order=True,
    )

    return prepared


def build_hierarchy(
    prepared: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    dim_state = pl.DataFrame(
        {
            "state_key": [1],
            "state_code": ["AL"],
            "department_name": ["Alabama State Department of Education"],
        }
    ).with_columns(
        [
            pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_created_at"),
            pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_updated_at"),
        ]
    )

    district_seed = (
        prepared.filter(
            (pl.col("row_type").is_in(["DISTRICT", "SCHOOL"]))
            & (~pl.col("dist_name_norm").str.contains("state department of education"))
        )
        .sort(
            by=[
                "state_code",
                "dist_name_norm",
                "state_dist_id",
                "nces_admin_id",
                "dist_name",
            ],
            descending=[False, False, True, True, False],
            nulls_last=True,
        )
        .unique(
            subset=["state_code", "dist_name_norm"], keep="first", maintain_order=True
        )
        .sort(by=["state_code", "dist_name"])
        .with_row_index(name="district_key", offset=1)
    )

    dim_district = district_seed.select(
        [
            pl.col("district_key").cast(pl.Int64),
            pl.lit(1).cast(pl.Int64).alias("state_key"),
            "state_code",
            pl.col("dist_name").alias("district_name"),
            pl.col("dist_name_norm").alias("district_name_norm"),
            pl.col("state_dist_id").cast(pl.Int64),
            pl.col("nces_admin_id").cast(pl.Int64),
            pl.col("source_state_dist_id"),
            pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_created_at"),
            pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_updated_at"),
        ]
    )

    school_seed = (
        prepared.filter(pl.col("row_type") == "SCHOOL")
        .sort(
            by=[
                "state_code",
                "dist_name_norm",
                "school_name_norm",
                "state_school_id",
                "nces_id",
                "school_name",
            ],
            descending=[False, False, False, True, True, False],
            nulls_last=True,
        )
        .unique(
            subset=["state_code", "dist_name_norm", "school_name_norm"],
            keep="first",
            maintain_order=True,
        )
    )

    school_with_district = school_seed.join(
        dim_district.select(["district_key", "state_code", "district_name_norm"]),
        left_on=["state_code", "dist_name_norm"],
        right_on=["state_code", "district_name_norm"],
        how="inner",
    )

    dim_school = (
        school_with_district.sort(by=["district_key", "school_name"])
        .with_row_index(name="school_key", offset=1)
        .select(
            [
                pl.col("school_key").cast(pl.Int64),
                pl.col("district_key").cast(pl.Int64),
                "state_code",
                pl.col("school_name"),
                pl.col("school_name_norm"),
                pl.col("state_school_id").cast(pl.Int64),
                pl.col("nces_geo_id").cast(pl.Int64),
                pl.col("census_id").cast(pl.Int64),
                pl.col("nces_id").cast(pl.Int64),
                "nces_charter",
                "nces_magnet",
                "nces_address",
                "nces_city",
                "nces_zip",
                "source_state_school_id",
                pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_created_at"),
                pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_updated_at"),
            ]
        )
    )

    school_map = dim_school.join(
        dim_district.select(["district_key", "state_code", "district_name_norm"]),
        on="district_key",
        how="inner",
    ).select(["school_key", "state_code", "district_name_norm", "school_name_norm"])

    bridge_school_year = (
        prepared.filter(pl.col("row_type") == "SCHOOL")
        .join(
            school_map,
            left_on=["state_code", "dist_name_norm", "school_name_norm"],
            right_on=["state_code", "district_name_norm", "school_name_norm"],
            how="inner",
        )
        .sort(
            by=[
                "school_key",
                "school_year_start",
                "state_school_id",
                "nces_id",
                "_ingested_at",
            ],
            descending=[False, False, True, True, True],
            nulls_last=True,
        )
        .unique(
            subset=["school_key", "school_year_start"],
            keep="first",
            maintain_order=True,
        )
        .select(
            [
                "school_key",
                "school_year_label",
                pl.col("school_year_start").cast(pl.Int64),
                pl.col("school_year_end").cast(pl.Int64),
                pl.col("nces_locale_key").cast(pl.Int64),
                "nces_locale_type",
                "nces_locale_subtype",
                "source_nces_locale",
                "_source_file",
                "_ingested_at",
                pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_created_at"),
                pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_updated_at"),
            ]
        )
    )

    dim_school_info = (
        bridge_school_year.join(dim_school, on="school_key", how="inner")
        .join(
            dim_district.select(
                [
                    "district_key",
                    "district_name",
                    "state_dist_id",
                    "nces_admin_id",
                    "source_state_dist_id",
                ]
            ),
            on="district_key",
            how="inner",
        )
        .select(
            [
                "school_key",
                "school_year_label",
                pl.col("school_year_start").cast(pl.Int64),
                pl.col("school_year_end").cast(pl.Int64),
                "state_code",
                pl.col("state_dist_id").cast(pl.Int64),
                pl.col("state_school_id").cast(pl.Int64),
                pl.col("nces_admin_id").cast(pl.Int64),
                pl.col("nces_geo_id").cast(pl.Int64),
                pl.col("census_id").cast(pl.Int64),
                pl.col("nces_id").cast(pl.Int64),
                pl.col("district_name").alias("dist_name"),
                "school_name",
                pl.col("nces_locale_key").cast(pl.Int64),
                "nces_locale_type",
                "nces_locale_subtype",
                "nces_charter",
                "nces_magnet",
                "nces_address",
                "nces_city",
                "nces_zip",
                "source_nces_locale",
                "source_state_dist_id",
                "source_state_school_id",
                "_source_file",
                "_ingested_at",
                pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_created_at"),
                pl.lit(datetime.now()).cast(pl.Datetime("us")).alias("_updated_at"),
            ]
        )
        .sort(by=["school_key", "school_year_start"])
    )

    return dim_state, dim_district, dim_school, bridge_school_year, dim_school_info


def guardrails(dim_school: pl.DataFrame, dim_school_info: pl.DataFrame) -> None:
    school_rows = dim_school.height
    if school_rows == 0:
        raise RuntimeError("dim_school_review would be empty")

    with_school_id = int(
        dim_school.select(pl.col("state_school_id").is_not_null().sum()).item() or 0
    )
    with_nces_id = int(
        dim_school.select(pl.col("nces_id").is_not_null().sum()).item() or 0
    )
    if with_school_id == 0 or with_nces_id == 0:
        raise RuntimeError(
            "Guardrail failed: dim_school_review has no non-null state_school_id or nces_id"
        )

    only_impute = (
        dim_school_info.select(pl.col("_source_file").n_unique()).item() == 1
        and dim_school_info.select(pl.col("_source_file").first()).item()
        == "impute_teacher_demographics"
    )
    if only_impute:
        raise RuntimeError("Guardrail failed: dim_school_info_review is imputation-only")

    dup_school_year = int(
        dim_school_info.group_by(["school_key", "school_year_start"])
        .len()
        .filter(pl.col("len") > 1)
        .height
    )
    if dup_school_year > 0:
        raise RuntimeError("Guardrail failed: duplicate (school_key, school_year_start)")


def write_all(connection_uri: str, frames: dict[str, pl.DataFrame]) -> None:
    for table_name in [
        "sandbox.dim_state_review",
        "sandbox.dim_district_review",
        "sandbox.dim_school_review",
        "sandbox.bridge_school_year_review",
        "sandbox.dim_school_info_review",
    ]:
        frames[table_name].write_database(
            table_name=table_name,
            connection=connection_uri,
            if_table_exists="replace",
            engine="adbc",
        )


def main() -> None:
    uri = db_uri()
    with psycopg.connect(uri) as conn:
        prepared = build_school_rows(conn)

    dim_state, dim_district, dim_school, bridge_school_year, dim_school_info = (
        build_hierarchy(prepared)
    )
    guardrails(dim_school, dim_school_info)

    frames = {
        "sandbox.dim_state_review": dim_state,
        "sandbox.dim_district_review": dim_district,
        "sandbox.dim_school_review": dim_school,
        "sandbox.bridge_school_year_review": bridge_school_year,
        "sandbox.dim_school_info_review": dim_school_info,
    }
    write_all(uri, frames)

    print(f"wrote_dim_state={dim_state.height}")
    print(f"wrote_dim_district={dim_district.height}")
    print(f"wrote_dim_school={dim_school.height}")
    print(f"wrote_bridge_school_year={bridge_school_year.height}")
    print(f"wrote_dim_school_info={dim_school_info.height}")
    print(
        "coverage_state_school_id="
        f"{int(dim_school.select(pl.col('state_school_id').is_not_null().sum()).item() or 0)}"
    )
    print(
        "coverage_nces_id="
        f"{int(dim_school.select(pl.col('nces_id').is_not_null().sum()).item() or 0)}"
    )


if __name__ == "__main__":
    main()
