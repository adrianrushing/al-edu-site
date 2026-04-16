from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from psycopg import Connection
from psycopg.errors import LockNotAvailable, QueryCanceled

from app.db import get_connection
from app.querying import FilterParams, fetch_preview, get_dataset_or_none, iter_csv_rows
from app.schemas import DataPreviewResponse

router = APIRouter(tags=["data"])


def resolve_dataset_or_404(dataset: str):
    dataset_config = get_dataset_or_none(dataset)
    if dataset_config is None:
        raise HTTPException(status_code=404, detail=f"Unknown dataset '{dataset}'")
    return dataset_config


def resolve_filters(
    year: int | None,
    school_key: int | None,
    district: str | None,
    school: str | None,
    gender: str | None,
    race: str | None,
    ethnicity: str | None,
    sub_population: str | None,
    grade: str | None,
) -> FilterParams:
    return FilterParams(
        year=year,
        school_key=school_key,
        district=district,
        school=school,
        gender=gender,
        race=race,
        ethnicity=ethnicity,
        sub_population=sub_population,
        grade=grade,
    )


@router.get("/data/{dataset}", response_model=DataPreviewResponse)
def preview_dataset(
    dataset: str,
    year: int | None = None,
    school_key: int | None = None,
    district: str | None = None,
    school: str | None = None,
    gender: str | None = None,
    race: str | None = None,
    ethnicity: str | None = None,
    sub_population: str | None = None,
    grade: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_connection),
) -> DataPreviewResponse:
    config = resolve_dataset_or_404(dataset)
    filters = resolve_filters(
        year,
        school_key,
        district,
        school,
        gender,
        race,
        ethnicity,
        sub_population,
        grade,
    )

    try:
        rows = fetch_preview(conn, config, filters, limit=limit, offset=offset)
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc

    return DataPreviewResponse(
        dataset=config.key,
        limit=limit,
        offset=offset,
        row_count=len(rows),
        rows=rows,
    )


@router.get("/download/{dataset}.csv")
def download_dataset_csv(
    dataset: str,
    year: int | None = None,
    school_key: int | None = None,
    district: str | None = None,
    school: str | None = None,
    gender: str | None = None,
    race: str | None = None,
    ethnicity: str | None = None,
    sub_population: str | None = None,
    grade: str | None = None,
    conn: Connection = Depends(get_connection),
) -> StreamingResponse:
    config = resolve_dataset_or_404(dataset)
    filters = resolve_filters(
        year,
        school_key,
        district,
        school,
        gender,
        race,
        ethnicity,
        sub_population,
        grade,
    )

    if config.requires_filter_for_download and not filters.has_any_filter():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Dataset '{config.key}' requires at least one filter for CSV download. "
                "Use year, school_key, district, or school."
            ),
        )

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{config.key}_{timestamp}.csv"

    try:
        stream = iter_csv_rows(conn, config, filters)
        return StreamingResponse(
            stream,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except (LockNotAvailable, QueryCanceled) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is busy processing another job. Retry shortly.",
        ) from exc
