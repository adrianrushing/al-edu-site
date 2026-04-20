import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from psycopg import Connection
from psycopg.errors import LockNotAvailable, QueryCanceled, UndefinedTable
from psycopg.rows import dict_row

from app.db import get_connection
from app.schemas import (
    DistrictRankingItem,
    DistrictRankingsResponse,
    DistrictSchoolItem,
    DistrictSchoolsResponse,
    SchoolPerformancePoint,
    SchoolPerformanceResponse,
)

router = APIRouter(prefix="/rankings", tags=["rankings"])


def encode_cursor(*parts: int | str) -> str:
    payload = json.dumps(list(parts), separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decode_cursor(cursor: str, expected_parts: int) -> list[int | str]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        parts = json.loads(decoded)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc

    if not isinstance(parts, list) or len(parts) != expected_parts:
        raise HTTPException(status_code=400, detail="Invalid cursor")

    return parts


def resolve_year(conn: Connection, year: int | None) -> int:
    if year is not None:
        return year

    with conn.cursor() as cur:
        cur.execute("SELECT MAX(year) FROM core.fact_edunomics")
        latest = cur.fetchone()

    if not latest or latest[0] is None:
        raise HTTPException(status_code=404, detail="No funding year data available")

    return int(latest[0])


def district_rankings_from_mv(
    conn: Connection,
    selected_year: int,
    limit: int,
    cursor: str | None,
) -> list[dict[str, object]]:
    params: list[object] = [selected_year]
    cursor_filter = ""
    if cursor:
        funding_rank, district_key = decode_cursor(cursor, expected_parts=2)
        params.extend([int(funding_rank), int(funding_rank), int(district_key)])
        cursor_filter = (
            "AND (funding_rank > %s OR (funding_rank = %s AND district_key > %s))"
        )

    params.append(limit + 1)
    query = f"""
        SELECT
            district_key,
            district_name,
            year,
            school_count,
            avg_per_pupil_funding,
            avg_achievement,
            funding_rank
        FROM core.mv_district_year_funding_performance
        WHERE year = %s
        {cursor_filter}
        ORDER BY funding_rank ASC, district_key ASC
        LIMIT %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)  # pyright: ignore[reportArgumentType]
        return [dict(row) for row in cur.fetchall()]


def district_rankings_live(
    conn: Connection,
    selected_year: int,
    limit: int,
    cursor: str | None,
) -> list[dict[str, object]]:
    params: list[object] = [selected_year, selected_year, selected_year]
    cursor_filter = ""
    if cursor:
        funding_rank, district_key = decode_cursor(cursor, expected_parts=2)
        params.extend([int(funding_rank), int(funding_rank), int(district_key)])
        cursor_filter = (
            "WHERE funding_rank > %s OR (funding_rank = %s AND district_key > %s)"
        )

    params.append(limit + 1)

    query = f"""
        WITH district_aggregates AS (
            SELECT
                d.district_key,
                d.district_name,
                %s::smallint AS year,
                COUNT(DISTINCT s.school_key)::integer AS school_count,
                AVG(e.per_pupil_total_raw)::double precision AS avg_per_pupil_funding,
                AVG(o.ach_all)::double precision AS avg_achievement
            FROM core.dim_district d
            JOIN core.dim_school s
                ON s.district_key = d.district_key
            LEFT JOIN core.fact_edunomics e
                ON e.school_key = s.school_key
                AND e.year = %s
            LEFT JOIN core.fact_school_outcomes_wide o
                ON o.school_key = s.school_key
                AND o.year = %s
            GROUP BY d.district_key, d.district_name
        ), ranked AS (
            SELECT
                district_key,
                district_name,
                year,
                school_count,
                avg_per_pupil_funding,
                avg_achievement,
                DENSE_RANK() OVER (
                    ORDER BY avg_per_pupil_funding DESC NULLS LAST
                )::integer AS funding_rank
            FROM district_aggregates
        )
        SELECT
            district_key,
            district_name,
            year,
            school_count,
            avg_per_pupil_funding,
            avg_achievement,
            funding_rank
        FROM ranked
        {cursor_filter}
        ORDER BY funding_rank ASC, district_key ASC
        LIMIT %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)  # pyright: ignore[reportArgumentType]
        return [dict(row) for row in cur.fetchall()]


@router.get("/districts", response_model=DistrictRankingsResponse)
def get_district_rankings(
    year: int | None = Query(default=None, ge=2000, le=2100),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = None,
    conn: Connection = Depends(get_connection),
) -> DistrictRankingsResponse:
    selected_year = resolve_year(conn, year)

    try:
        try:
            rows = district_rankings_from_mv(conn, selected_year, limit, cursor)
        except UndefinedTable:
            rows = district_rankings_live(conn, selected_year, limit, cursor)
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc

    next_cursor: str | None = None
    if len(rows) > limit:
        last = DistrictRankingItem.model_validate(rows[limit - 1])
        next_cursor = encode_cursor(last.funding_rank, last.district_key)
        rows = rows[:limit]

    items = [DistrictRankingItem.model_validate(row) for row in rows]

    return DistrictRankingsResponse(
        year=selected_year,
        limit=limit,
        next_cursor=next_cursor,
        items=items,
    )


@router.get("/districts/{district_key}/schools", response_model=DistrictSchoolsResponse)
def get_district_schools(
    district_key: int = Path(..., ge=1),
    year: int | None = Query(default=None, ge=2000, le=2100),
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str | None = None,
    conn: Connection = Depends(get_connection),
) -> DistrictSchoolsResponse:
    selected_year = resolve_year(conn, year)

    params: list[object] = [selected_year, selected_year, selected_year, district_key]
    cursor_filter = ""
    if cursor:
        school_name, school_key = decode_cursor(cursor, expected_parts=2)
        params.extend([str(school_name), str(school_name), int(school_key)])
        cursor_filter = (
            "AND (si.school_name > %s OR (si.school_name = %s AND s.school_key > %s))"
        )

    params.append(limit + 1)

    query = f"""
        SELECT
            d.district_key,
            d.district_name,
            s.school_key,
            si.school_name,
            %s::smallint AS year,
            e.per_pupil_total_raw::double precision AS per_pupil_total_raw,
            o.ach_all::double precision AS ach_all
        FROM core.dim_school s
        JOIN core.dim_district d
            ON d.district_key = s.district_key
        JOIN core.dim_school_info si
            ON si.school_key = s.school_key
        LEFT JOIN core.fact_edunomics e
            ON e.school_key = s.school_key
            AND e.year = %s
        LEFT JOIN core.fact_school_outcomes_wide o
            ON o.school_key = s.school_key
            AND o.year = %s
        WHERE s.district_key = %s
        {cursor_filter}
        ORDER BY si.school_name ASC, s.school_key ASC
        LIMIT %s
    """

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)  # pyright: ignore[reportArgumentType]
            rows = [dict(row) for row in cur.fetchall()]
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc

    next_cursor: str | None = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(str(last["school_name"]), int(last["school_key"]))
        rows = rows[:limit]

    items = [DistrictSchoolItem.model_validate(row) for row in rows]

    return DistrictSchoolsResponse(
        district_key=district_key,
        year=selected_year,
        limit=limit,
        next_cursor=next_cursor,
        items=items,
    )


@router.get(
    "/schools/{school_key}/performance", response_model=SchoolPerformanceResponse
)
def get_school_performance(
    school_key: int = Path(..., ge=1),
    from_year: int | None = Query(default=None, ge=2000, le=2100),
    to_year: int | None = Query(default=None, ge=2000, le=2100),
    conn: Connection = Depends(get_connection),
) -> SchoolPerformanceResponse:
    params: list[object] = [school_key]
    year_filter = ""
    if from_year is not None:
        params.append(from_year)
        year_filter += " AND COALESCE(e.year, o.year) >= %s"
    if to_year is not None:
        params.append(to_year)
        year_filter += " AND COALESCE(e.year, o.year) <= %s"

    query = f"""
        SELECT
            COALESCE(e.year, o.year)::integer AS year,
            e.per_pupil_total_raw::double precision AS per_pupil_total_raw,
            o.ach_all::double precision AS ach_all,
            o.grw_all::double precision AS grw_all,
            o.abs_all::double precision AS abs_all
        FROM core.fact_edunomics e
        FULL OUTER JOIN core.fact_school_outcomes_wide o
            ON o.school_key = e.school_key
            AND o.year = e.year
        WHERE COALESCE(e.school_key, o.school_key) = %s
        {year_filter}
        ORDER BY year DESC
    """

    school_query = """
        SELECT school_name, dist_name
        FROM core.dim_school_info
        WHERE school_key = %s
        LIMIT 1
    """

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(school_query, (school_key,))
            school_row = cur.fetchone()
            cur.execute(query, params)  # pyright: ignore[reportArgumentType]
            points = [dict(row) for row in cur.fetchall()]
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc

    school_name = None
    district_name = None
    if school_row is not None:
        school_name = school_row.get("school_name")
        district_name = school_row.get("dist_name")

    point_models = [SchoolPerformancePoint.model_validate(point) for point in points]

    return SchoolPerformanceResponse(
        school_key=school_key,
        school_name=school_name,
        district_name=district_name,
        from_year=from_year,
        to_year=to_year,
        points=point_models,
    )
