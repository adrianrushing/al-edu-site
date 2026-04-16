from collections.abc import Generator

from fastapi import Request
from psycopg import Connection
from psycopg_pool import ConnectionPool

from app.config import settings


def create_pool() -> ConnectionPool:
    pool = ConnectionPool(conninfo=settings.database_url, max_size=20, timeout=15)
    pool.open(wait=True)
    return pool


def get_connection(request: Request) -> Generator[Connection, None, None]:
    pool: ConnectionPool = request.app.state.db_pool
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET lock_timeout = '3s'")
            cur.execute("SET statement_timeout = '45s'")
            cur.execute("SET default_transaction_read_only = on")
        yield conn
