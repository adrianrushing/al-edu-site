import csv
import io
from collections.abc import Iterator
from typing import Any

from psycopg import Connection, sql
from psycopg.rows import dict_row

from app.datasets import DATASETS, DIM_COLUMNS, DatasetConfig


class FilterParams:
    def __init__(
        self,
        year: int | None = None,
        school_key: int | None = None,
        district: str | None = None,
        school: str | None = None,
        gender: str | None = None,
        race: str | None = None,
        ethnicity: str | None = None,
        sub_population: str | None = None,
        grade: str | None = None,
    ) -> None:
        self.year = year
        self.school_key = school_key
        self.district = district
        self.school = school
        self.gender = gender
        self.race = race
        self.ethnicity = ethnicity
        self.sub_population = sub_population
        self.grade = grade

    def has_any_filter(self) -> bool:
        return any(
            [
                self.year is not None,
                self.school_key is not None,
                bool(self.district),
                bool(self.school),
                bool(self.gender),
                bool(self.race),
                bool(self.ethnicity),
                bool(self.sub_population),
                bool(self.grade),
            ]
        )


def get_dataset_or_none(dataset: str) -> DatasetConfig | None:
    return DATASETS.get(dataset)


def build_where_clauses(
    config: DatasetConfig, params: FilterParams
) -> tuple[list[sql.Composable], list[Any]]:
    clauses: list[sql.Composable] = []
    values: list[Any] = []

    if params.year is not None:
        clauses.append(sql.SQL("f.year = %s"))
        values.append(params.year)

    if params.school_key is not None:
        clauses.append(sql.SQL("f.school_key = %s"))
        values.append(params.school_key)

    if params.district:
        clauses.append(sql.SQL("d.dist_name ILIKE %s"))
        values.append(f"%{params.district}%")

    if params.school:
        clauses.append(sql.SQL("d.school_name ILIKE %s"))
        values.append(f"%{params.school}%")

    dataset_columns = set(config.columns)

    if params.gender and "gender" in dataset_columns:
        clauses.append(sql.SQL("f.gender = %s"))
        values.append(params.gender)

    if params.race and "race" in dataset_columns:
        clauses.append(sql.SQL("f.race = %s"))
        values.append(params.race)

    if params.ethnicity and "ethnicity" in dataset_columns:
        clauses.append(sql.SQL("f.ethnicity = %s"))
        values.append(params.ethnicity)

    if params.sub_population and "sub_population" in dataset_columns:
        clauses.append(sql.SQL("f.sub_population = %s"))
        values.append(params.sub_population)

    if params.grade and "grade" in dataset_columns:
        clauses.append(sql.SQL("f.grade = %s"))
        values.append(params.grade)

    return clauses, values


def select_columns(config: DatasetConfig) -> sql.Composed:
    dim_select = [
        sql.SQL("d.") + sql.Identifier(col) + sql.SQL(" AS ") + sql.Identifier(col)
        for col in DIM_COLUMNS
    ]
    fact_select = [
        sql.SQL("f.") + sql.Identifier(col) + sql.SQL(" AS ") + sql.Identifier(col)
        for col in config.columns
    ]
    return sql.SQL(", ").join(dim_select + fact_select)


def build_dataset_query(
    config: DatasetConfig,
    params: FilterParams,
    *,
    limit: int | None,
    offset: int | None,
) -> tuple[sql.Composed, list[Any]]:
    where_clauses, values = build_where_clauses(config, params)
    columns = select_columns(config)

    query = sql.SQL(
        "SELECT {columns} "
        "FROM core.{table} f "
        "JOIN core.dim_school_info d ON d.school_key = f.school_key"
    ).format(columns=columns, table=sql.Identifier(config.table_name))

    if where_clauses:
        query = query + sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_clauses)

    query = query + sql.SQL(
        " ORDER BY d.school_year_start DESC, d.dist_name, d.school_name, f.school_key"
    )

    if limit is not None:
        query = query + sql.SQL(" LIMIT %s")
        values.append(limit)

    if offset is not None:
        query = query + sql.SQL(" OFFSET %s")
        values.append(offset)

    return query, values


def fetch_preview(
    conn: Connection,
    config: DatasetConfig,
    params: FilterParams,
    *,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    query, values = build_dataset_query(config, params, limit=limit, offset=offset)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, values)
        return [dict(row) for row in cur.fetchall()]


def iter_csv_rows(
    conn: Connection,
    config: DatasetConfig,
    params: FilterParams,
    *,
    chunk_size: int = 5000,
) -> Iterator[str]:
    query, values = build_dataset_query(config, params, limit=None, offset=None)
    selected_columns = [*DIM_COLUMNS, *config.columns]

    header_buffer = io.StringIO()
    header_writer = csv.writer(header_buffer)
    header_writer.writerow(selected_columns)
    yield header_buffer.getvalue()

    with conn.cursor(name=f"csv_{config.key}") as cur:
        cur.itersize = chunk_size
        cur.execute(query, values)

        while True:
            rows = cur.fetchmany(chunk_size)
            if not rows:
                break

            chunk_buffer = io.StringIO()
            writer = csv.writer(chunk_buffer)
            for row in rows:
                writer.writerow(row)
            yield chunk_buffer.getvalue()
