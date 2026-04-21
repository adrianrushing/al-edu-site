# AGENTS.md

This file guides agentic coding tools in this repository. Keep changes small, follow
existing patterns, and update this file when workflows change.

## Repository Overview

- Monorepo with npm workspaces under `apps/*`.
- Frontend: React + TypeScript + Vite + Tailwind in `apps/web`.
- Backend API: FastAPI in `apps/api`.
- Pipeline app under `apps/pipeline` (Python, uv_build).
- Data cleaning package under `data_cleaning` (Python, uv_build).

## Build, Lint, Test

### Root commands

- Dev (web): `npm run dev`
- Dev (API): `npm run dev:api`
- Build (web): `npm run build`
- Docker compose: `npm run docker:up`, `npm run docker:down`, `npm run docker:reset`

### Frontend (apps/web)

- Dev server: `npm run dev -w apps/web`
- Build: `npm run build -w apps/web`
- Lint: `npm run lint -w apps/web`

Single test: no test runner configured in repo.
If you add tests, also add a `test` script and document a per-test command.

### Backend API (apps/api)

- Run locally: `uv run --project apps/api python -m uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000`

Single test: no test runner configured in repo.
If you add tests, prefer `pytest` and document `pytest path/to/test.py::test_name`.

- When new endpoints are added, add them to the ./API_ENDPOINTS.md

### Pipelines

- Sync deps: `uv sync --project apps/pipeline`
- Status: `uv run --project apps/pipeline python -m pipeline.cli status`
- Plan: `uv run --project apps/pipeline python -m pipeline.cli plan`
- Apply: `uv run --project apps/pipeline python -m pipeline.cli apply`
- Dry run: `uv run --project apps/pipeline python -m pipeline.cli apply --dry-run`

### Data cleaning package (data_cleaning)

- Run package entrypoint: `python -m data_cleaning`
- Refresh review SQL tables: `psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/sandbox_refresh_all_review.sql`
- Load reviewed tables to core: `psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/core_load_review_to_core.sql`
- Load reviewed geographic tables to core: `psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/core_load_geo_to_core.sql`
- Report school-county strict nulls: `psql "$DATABASE_URL" -f data_cleaning/src/data_cleaning/sql/geo_strict_null_report.sql`

Single test: no test runner configured in repo.

## Code Style Guidelines

### General

- Match existing formatting in each file; do not reformat unrelated code.
- Keep edits minimal and scoped to the requested change.
- Prefer explicit, readable code over cleverness.
- Avoid introducing new dependencies unless required.

### TypeScript / React (apps/web)

Imports
- Use absolute path alias `@/` for app code (see `apps/web/tsconfig.json`).
- Keep third-party imports before local imports.
- Group imports by origin and separate with a blank line when it improves readability.

Formatting
- The repo mixes single and double quotes; respect the file’s current style.
- Use trailing commas where already present; do not normalize formatting.
- Keep JSX props readable; wrap only when lines become long.

Types
- Use TypeScript types and interfaces for public component props and API data.
- Prefer `type` for unions and mapped types; use `interface` for object shapes.
- Keep types close to usage (same file) unless shared across modules.

Naming
- Components: `PascalCase`.
- Hooks: `useX`.
- Variables/functions: `camelCase`.
- Files: match existing conventions (pages are kebab-case in `src/pages`).

State and data
- Prefer TanStack Query for server data; avoid ad-hoc fetch in components when
  queries already exist.
- Centralize API calls in `apps/web/src/lib/api`.

Error handling
- Use helpers in `apps/web/src/lib/api.ts` for consistent API errors.
- Propagate errors to the UI via TanStack Query error states.

Styling
- Use Tailwind utility classes and existing UI components in `src/components/ui`.
- Use `cn` from `apps/web/src/lib/utils.ts` to merge class names.
- Avoid adding global CSS unless absolutely necessary.

Routing
- Routes are configured in `apps/web/src/router.tsx` via TanStack Router.
- Route page components are under `apps/web/src/pages`.



Frontend Architecture & Modularization Rules:

    Component Size Limits: Never write React components exceeding 150-200 lines. If a file grows larger, you MUST extract sub-components or business logic.

    Separation of Concerns: Keep UI rendering separate from business logic. Extract complex state, data fetching (TanStack Query), and event handling into custom hooks (e.g., use[FeatureName].ts).

    UI Component Reuse: Always check apps/web/src/components/ui for existing Radix/Tailwind components before creating new atomic elements. Do not duplicate UI logic.

    Feature Grouping: Do not put complex logic directly in src/routes. Create feature-specific folders (e.g., src/features/districts/components/...) and import them into the TanStack router files.

    Props & Types: Explicitly define interface blocks for all component props in the same file. Do not use inline any types.

    Before modifying any frontend code, output a brief 'Architecture Plan' detailing: 1) Which files you will touch, 2) The new sub-components you plan to extract, and 3) The custom hooks you will create. Only proceed with writing code once the plan is established.


Formatting & Validation Rules:

    Biome Formatting: All code must adhere to the rules defined in biome.json: use 4-space indentation and a 90-character line width. Do not format unrelated code.

    Frontend Linting: After generating React/TypeScript code, you must assume the code will be validated against the ESLint rules defined in apps/web (npm run lint -w apps/web). Ensure no unused directives or React-hooks violations occur.

    Typescript strictness: Follow the tsconfig.json paths utilizing @/ for absolute imports, placing third-party imports before local ones.

    Python Patterns (apps/api & apps/pipelines): Use concrete type hints (Path, dict[str, str]) instead of Any. Keep 4-space indentation. Maintain pure transformations using Polars lazy() idioms for data pipelines.


### Python (apps/api, apps/pipeline, data_cleaning)

Imports
- Standard library first, then third-party, then local imports.
- Keep imports explicit; avoid unused imports.

Formatting
- No formatter config found; keep existing style (4-space indentation).
- Limit line length sensibly; wrap long function calls.

Types
- Add type hints for new public functions where reasonable.
- Use concrete types (e.g., `Path`, `dict[str, str]`) over `Any`.

Naming
- Functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.

Error handling
- Prefer explicit exception handling with a clear message.
- In data pipelines, log enough context to diagnose file failures.

### API conventions (apps/api)

- FastAPI application is defined in `apps/api/app/main.py`.
- Routes are organized under `apps/api/app/routes/*.py` and registered in `main.py`.
- Configuration is in `apps/api/app/config.py`.
- Do not introduce DB usage without also configuring connection settings in `Settings`.

### Data cleaning package (data_cleaning)

- Keep file processing deterministic and avoid side effects outside `flat_data`.
- Use `pathlib.Path` for paths.

## Configuration and Rules

- No Cursor rules found in `.cursor/rules/` or `.cursorrules`.
- No Copilot rules found in `.github/copilot-instructions.md`.

## Hard Checks

All commits must pass Ruff and Biome validation. Run npx biome check --apply . and ruff check --fix . before pushing.

## If You Add Tests

- Prefer a single test runner per language:
  - JS/TS: add `vitest` (or similar) and document `npm run test -w apps/web`.
  - Python: add `pytest` and document `pytest path/to/test.py::test_name`.
- Update this file with the exact per-test command.
