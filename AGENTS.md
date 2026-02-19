# AGENTS.md

This file guides agentic coding tools in this repository. Keep changes small, follow
existing patterns, and update this file when workflows change.

## Repository Overview

- Monorepo with npm workspaces under `apps/*`.
- Frontend: React + TypeScript + Vite + Tailwind in `apps/web`.
- Backend API: Flask in `apps/api`.
- Data pipelines: Python + Polars in `apps/pipelines`.
- Data cleaning package under `data_cleaning` (Python, uv_build).

## Build, Lint, Test

### Root commands

- Dev (web + API): `npm run dev`
- Build (web): `npm run build`
- Install all deps: `npm run install:all`
- Docker compose: `npm run docker:up`, `npm run docker:down`, `npm run docker:reset`

### Frontend (apps/web)

- Dev server: `npm run dev -w apps/web`
- Build: `npm run build -w apps/web`
- Lint: `npm run lint -w apps/web`

Single test: no test runner configured in repo.
If you add tests, also add a `test` script and document a per-test command.

### Backend API (apps/api)

- Run locally: `python apps/api/app/run.py`

Single test: no test runner configured in repo.
If you add tests, prefer `pytest` and document `pytest path/to/test.py::test_name`.

### Pipelines (apps/pipelines)

- Run sample clean: `python apps/pipelines/silver/sample_clean.py`

Single test: no test runner configured in repo.

### Data cleaning package (data_cleaning)

- Run package entrypoint: `python -m data_cleaning`

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
- Files: match existing conventions (routes are kebab-case in `src/routes`).

State and data
- Prefer TanStack Query for server data; avoid ad-hoc fetch in components when
  queries already exist.
- Centralize API calls in `apps/web/src/lib/api`.

Error handling
- Use `fetchApi` in `apps/web/src/lib/api/client.ts` for consistent API errors.
- Propagate errors to the UI via TanStack Query error states.

Styling
- Use Tailwind utility classes and existing UI components in `src/components/ui`.
- Use `cn` from `apps/web/src/lib/utils.ts` to merge class names.
- Avoid adding global CSS unless absolutely necessary.

Routing
- Routes live under `apps/web/src/routes` and use TanStack Router file-based
  conventions.
- Update `routeTree.gen.ts` only via the router tooling if needed.

### Python (apps/api, apps/pipelines, data_cleaning)

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

- Flask app factory lives in `apps/api/app/__init__.py`.
- Routes use blueprints (`apps/api/app/routes.py`).
- Configuration is in `apps/api/app/config.py`.
- Do not introduce DB usage without also configuring SQLAlchemy and connection
  settings in `Config`.

### Data pipelines (apps/pipelines)

- Use Polars idioms (`lazy()` when appropriate) and keep transformations pure.
- Read/write paths should be explicit and logged.

### Data cleaning package (data_cleaning)

- Keep file processing deterministic and avoid side effects outside `flat_data`.
- Use `pathlib.Path` for paths.

## Configuration and Rules

- No Cursor rules found in `.cursor/rules/` or `.cursorrules`.
- No Copilot rules found in `.github/copilot-instructions.md`.

## If You Add Tests

- Prefer a single test runner per language:
  - JS/TS: add `vitest` (or similar) and document `npm run test -w apps/web`.
  - Python: add `pytest` and document `pytest path/to/test.py::test_name`.
- Update this file with the exact per-test command.
