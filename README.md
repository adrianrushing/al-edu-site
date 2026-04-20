# EFLT Monorepo

## PostgreSQL access

In pgAdmin, use:

- Host: `local_db`
- Port: `5432`
- Maintenance database: `eflt`
- Username: `dev_user`
- Password: `dev_password`

From host machine tools (`psql`, FastAPI local runs), use:

- Host: `localhost`
- Port: `5433`
- Database: `eflt`
- Username: `dev_user`
- Password: `dev_password`

## Run API (FastAPI)

```bash
uv sync --project apps/api
uv run --project apps/api python -m uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000
```

API runs on `http://localhost:8000`.

## Run frontend (TanStack Router + Vite)

```bash
npm install -w apps/web
npm run dev -w apps/web
```

Frontend runs on `http://localhost:5173`.

Set API base URL if needed:

```bash
cp apps/web/.env.example apps/web/.env
```

## Useful API endpoints

- `GET /health`
- `GET /datasets`
- `GET /filters`
- `GET /schools?q=...&year=...`
- `GET /data/{dataset}?year=...&limit=...`
- `GET /download/{dataset}.csv?year=...`
