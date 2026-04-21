import math
import os

import joblib
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from psycopg import Connection
from psycopg.errors import LockNotAvailable, QueryCanceled, UndefinedTable
from psycopg.rows import dict_row

from app.datasets import COMMON_FILTERS, DATASETS
from app.db import get_connection
from app.schemas import (
    DatasetInfo,
    FiltersResponse,
    SchoolItem,
    SchoolMetadataResponse,
    SchoolSimulationMetadataResponse,
    SchoolSimulationYearStatus,
)

router = APIRouter(tags=["metadata"])

_ACHIEVEMENT_FEATURES_CACHE: list[str] | None = None
_SIMULATION_RACES = [
    "American Indian/Alaska Native",
    "Asian",
    "Black or African American",
    "Native Hawaiian/Pacific Islander",
    "Two or More Races",
    "White",
]


CORE_TABLES_MISSING_DETAIL = (
    "Core data tables are not loaded. Run the data load scripts to create core.* "
    "tables and materialized views."
)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _get_achievement_features() -> list[str]:
    global _ACHIEVEMENT_FEATURES_CACHE

    if _ACHIEVEMENT_FEATURES_CACHE is not None:
        return _ACHIEVEMENT_FEATURES_CACHE

    model_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "models",
        "ach_all_model.joblib",
    )
    if not os.path.exists(model_path):
        raise HTTPException(status_code=503, detail="Achievement model file is missing")

    model_data = joblib.load(model_path)
    features = model_data.get("features") if isinstance(model_data, dict) else None
    if not isinstance(features, list):
        raise HTTPException(
            status_code=500,
            detail="Achievement model does not expose feature metadata",
        )

    _ACHIEVEMENT_FEATURES_CACHE = [str(feature) for feature in features]
    return _ACHIEVEMENT_FEATURES_CACHE


def _get_missing_features_for_year(
    cur,
    school_key: int,
    selected_year: int,
    required_features: list[str],
) -> list[str]:
    base_query = """
        SELECT
            e.per_pupil_total_raw,
            e.nces_poverty,
            e.nces_freelunch,
            t.exp_rate,
            t.inexp_rate,
            i.nces_locale_type,
            CASE WHEN i.nces_charter THEN 1 ELSE 0 END as is_charter,
            CASE WHEN i.nces_magnet THEN 1 ELSE 0 END as is_magnet
        FROM core.dim_school_info i
        LEFT JOIN core.fact_edunomics e
            ON e.school_key = i.school_key AND e.year = %s
        LEFT JOIN core.fact_teacher_experience t
            ON t.school_key = i.school_key AND t.year = %s
           AND t.sub_population = 'All SubPopulation'
        WHERE i.school_key = %s
        ORDER BY i.school_year_start DESC
        LIMIT 1
    """

    demo_query = """
        SELECT race, demographic_count
        FROM core.fact_student_demographics
        WHERE school_key = %s
          AND year = %s
          AND ethnicity = 'All Ethnicity'
          AND race != 'All Race'
    """

    cur.execute(
        base_query,
        (selected_year, selected_year, school_key),
    )
    base_row = cur.fetchone()
    base_columns = [desc.name for desc in cur.description]

    feature_values: dict[str, object] = {}
    if base_row is not None:
        feature_values.update(dict(zip(base_columns, base_row, strict=False)))

    cur.execute(demo_query, (school_key, selected_year))
    demo_rows = cur.fetchall()

    demo_counts = {race: 0.0 for race in _SIMULATION_RACES}
    for race, count in demo_rows:
        if race in demo_counts:
            demo_counts[race] = float(count) if count is not None else 0.0

    total_students = sum(demo_counts.values())
    for race in _SIMULATION_RACES:
        clean_name = "pct_" + race.lower().replace(" ", "_").replace("/", "_")
        if total_students > 0:
            feature_values[clean_name] = float(demo_counts[race] / total_students)
        else:
            feature_values[clean_name] = None

    return [
        feature
        for feature in required_features
        if _is_missing(feature_values.get(feature))
    ]


@router.get("/datasets", response_model=list[DatasetInfo])
def list_datasets() -> list[DatasetInfo]:
    return [
        DatasetInfo(
            key=dataset.key,
            description=dataset.description,
            filters=list(COMMON_FILTERS),
            requires_filter_for_download=dataset.requires_filter_for_download,
        )
        for dataset in DATASETS.values()
    ]


@router.get("/schools", response_model=list[SchoolItem])
def list_schools(
    q: str | None = Query(default=None, max_length=120),
    year: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_connection),
) -> list[SchoolItem]:
    params: list[object] = []
    where: list[str] = []

    if q:
        where.append("(dist_name ILIKE %s OR school_name ILIKE %s)")
        like = f"%{q.strip()}%"
        params.extend([like, like])

    if year is not None:
        where.append("school_year_start = %s")
        params.append(year)

    query = (
        "SELECT school_key, school_year_start, school_year_label, dist_name, school_name "
        "FROM core.dim_school_info"
    )
    if where:
        query = f"{query} WHERE {' AND '.join(where)}"

    query = f"{query} ORDER BY school_year_start DESC, dist_name, school_name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)  # pyright: ignore[reportArgumentType]  # type: ignore[arg-type]
            rows = cur.fetchall()
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc
    except UndefinedTable as exc:
        raise HTTPException(status_code=503, detail=CORE_TABLES_MISSING_DETAIL) from exc

    return [SchoolItem.model_validate(dict(row)) for row in rows]


@router.get("/filters", response_model=FiltersResponse)
def get_filters(conn: Connection = Depends(get_connection)) -> FiltersResponse:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT school_year_start FROM core.dim_school_info "
                "ORDER BY school_year_start DESC"
            )
            years = [row[0] for row in cur.fetchall()]

            cur.execute(
                "SELECT DISTINCT dist_name FROM core.dim_school_info "
                "WHERE dist_name IS NOT NULL AND dist_name <> '' "
                "ORDER BY dist_name LIMIT 500"
            )
            districts = [row[0] for row in cur.fetchall()]

            cur.execute(
                "SELECT canonical_value FROM ref.gender_canonical ORDER BY canonical_value"
            )
            genders = [row[0] for row in cur.fetchall()]

            cur.execute(
                "SELECT canonical_value FROM ref.race_canonical ORDER BY canonical_value"
            )
            races = [row[0] for row in cur.fetchall()]

            cur.execute(
                "SELECT canonical_value FROM ref.ethnicity_canonical ORDER BY canonical_value"
            )
            ethnicities = [row[0] for row in cur.fetchall()]
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc
    except UndefinedTable as exc:
        raise HTTPException(status_code=503, detail=CORE_TABLES_MISSING_DETAIL) from exc

    return FiltersResponse(
        years=years,
        districts=districts,
        genders=genders,
        races=races,
        ethnicities=ethnicities,
    )


@router.get("/schools/{school_key}/metadata", response_model=SchoolMetadataResponse)
def get_school_metadata(
    school_key: int = Path(..., ge=1),
    conn: Connection = Depends(get_connection),
) -> SchoolMetadataResponse:
    years_query = """
        SELECT DISTINCT school_year_start
        FROM core.dim_school_info
        WHERE school_key = %s
        ORDER BY school_year_start DESC
    """

    name_query = """
        SELECT school_name, dist_name
        FROM core.dim_school_info
        WHERE school_key = %s
        ORDER BY school_year_start DESC
        LIMIT 1
    """

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(years_query, (school_key,))
            year_rows = cur.fetchall()
            years: list[int] = [int(row["school_year_start"]) for row in year_rows]

            cur.execute(name_query, (school_key,))
            school_row = cur.fetchone()
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc
    except UndefinedTable as exc:
        raise HTTPException(status_code=503, detail=CORE_TABLES_MISSING_DETAIL) from exc

    if not years:
        raise HTTPException(status_code=404, detail="School not found")

    return SchoolMetadataResponse(
        school_key=school_key,
        school_name=school_row.get("school_name") if school_row else None,
        dist_name=school_row.get("dist_name") if school_row else None,
        available_years=years,
        latest_year=years[0] if years else None,
    )


@router.get(
    "/schools/{school_key}/simulation-metadata",
    response_model=SchoolSimulationMetadataResponse,
)
def get_school_simulation_metadata(
    school_key: int = Path(..., ge=1),
    year: int | None = Query(default=None),
    conn: Connection = Depends(get_connection),
) -> SchoolSimulationMetadataResponse:
    years_query = """
        SELECT year
        FROM (
            SELECT DISTINCT school_year_start::integer AS year
            FROM core.dim_school_info
            WHERE school_key = %s
            UNION
            SELECT DISTINCT year::integer AS year
            FROM core.fact_edunomics
            WHERE school_key = %s
            UNION
            SELECT DISTINCT year::integer AS year
            FROM core.fact_teacher_experience
            WHERE school_key = %s
              AND sub_population = 'All SubPopulation'
            UNION
            SELECT DISTINCT year::integer AS year
            FROM core.fact_student_demographics
            WHERE school_key = %s
              AND ethnicity = 'All Ethnicity'
              AND race != 'All Race'
        ) years
        ORDER BY year DESC
    """

    try:
        with conn.cursor() as cur:
            cur.execute(years_query, (school_key, school_key, school_key, school_key))
            available_years = [int(row[0]) for row in cur.fetchall()]

            if not available_years:
                raise HTTPException(status_code=404, detail="School not found")

            latest_year = available_years[0]
            required_features = _get_achievement_features()

            year_status: list[SchoolSimulationYearStatus] = []
            latest_simulatable_year: int | None = None

            for available_year in available_years:
                missing_features = _get_missing_features_for_year(
                    cur,
                    school_key,
                    available_year,
                    required_features,
                )
                is_simulatable = len(missing_features) == 0
                year_status.append(
                    SchoolSimulationYearStatus(
                        year=available_year,
                        is_simulatable=is_simulatable,
                        missing_features=missing_features,
                    )
                )
                if latest_simulatable_year is None and is_simulatable:
                    latest_simulatable_year = available_year

            if year is not None:
                selected_year = year
            elif latest_simulatable_year is not None:
                selected_year = latest_simulatable_year
            else:
                selected_year = latest_year

            if selected_year not in available_years:
                raise HTTPException(
                    status_code=400,
                    detail="Selected year is not available for this school",
                )

            selected_status = next(
                (status for status in year_status if status.year == selected_year),
                None,
            )
            selected_missing_features = (
                selected_status.missing_features if selected_status else []
            )
            selected_is_simulatable = (
                selected_status.is_simulatable if selected_status else False
            )

            return SchoolSimulationMetadataResponse(
                school_key=school_key,
                available_years=available_years,
                latest_year=latest_year,
                latest_simulatable_year=latest_simulatable_year,
                selected_year=selected_year,
                is_simulatable=selected_is_simulatable,
                missing_features=selected_missing_features,
                year_status=year_status,
            )
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc
    except UndefinedTable as exc:
        raise HTTPException(status_code=503, detail=CORE_TABLES_MISSING_DETAIL) from exc
