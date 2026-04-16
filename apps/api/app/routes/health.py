from fastapi import APIRouter, Depends
from psycopg import Connection

from app.db import get_connection
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(conn: Connection = Depends(get_connection)) -> HealthResponse:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    return HealthResponse(status="ok", database="ok")
