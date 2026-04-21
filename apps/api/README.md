# EFLT FastAPI

## Run locally

```bash
uv sync --project apps/api
uv run --project apps/api python -m uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000
```

## Environment variables

- `DATABASE_URL` (default: `postgresql://dev_user:dev_password@localhost:5433/eflt`)
- `APP_HOST` (default: `0.0.0.0`)
- `APP_PORT` (default: `8000`)
- `CORS_ORIGINS` (JSON list, default: `["http://localhost:5173"]`)

## Endpoints

- `GET /health`
- `GET /datasets`
- `GET /schools`
- `GET /schools/{school_key}/metadata`
- `GET /filters`
- `GET /data/{dataset}`
- `GET /download/{dataset}.csv`
- `GET /predict/baseline/{school_key}/{year}`
- `POST /predict/{target_variable}`
- `GET /rankings/districts`
- `GET /rankings/districts/{district_key}/schools`
- `GET /rankings/schools/{school_key}/performance`
