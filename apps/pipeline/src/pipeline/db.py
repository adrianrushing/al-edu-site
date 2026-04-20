import psycopg
from psycopg import Connection

from pipeline.config import get_settings


def connect() -> Connection:
    settings = get_settings()
    return psycopg.connect(settings.database_url)
