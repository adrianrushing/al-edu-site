from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import LockNotAvailable, QueryCanceled
from psycopg.rows import dict_row

from app.datasets import COMMON_FILTERS, DATASETS
from app.db import get_connection
from app.schemas import (
    DatasetInfo,
    FiltersResponse,
    SchoolItem,
)

router = APIRouter(tags=["metadata"])


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
            cur.execute(query, params)  # pyright: ignore[reportArgumentType]
            rows = cur.fetchall()
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc

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

    return FiltersResponse(
        years=years,
        districts=districts,
        genders=genders,
        races=races,
        ethnicities=ethnicities,
    )
