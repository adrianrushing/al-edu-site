from functools import lru_cache
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL cannot be empty")
        if not value.startswith("postgresql://") and not value.startswith("postgres://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


def get_raw_data_dir() -> Path:
    env_path = os.getenv("FLAT_DATA_RAW_DIR")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).resolve().parents[4] / "flat_data" / "in" / "raw_data"
