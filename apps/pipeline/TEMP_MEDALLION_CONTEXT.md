# Temporary Context: Medallion Schema Migration

## Decision Snapshot

We are rebuilding the DB structure with medallion naming.

- raw -> bronze
- staging -> silver
- core -> gold
- materialized views -> platinum
- sandbox unchanged
- ref unchanged

## Rationale

- Keep naming aligned to pipeline responsibilities and future unseen-data reruns.
- Separate heavy read models from serving tables by moving MVs to `platinum`.

## Complexity Recommendation

- Keep `ref`: low complexity, high integrity, API depends on canonical filters.
- Keep `sandbox`: medium/high complexity but important for review, dedupe, and imputation verification.

## Operational Constraint

- Pipeline creates structure only in this phase.
- Existing local DB is not targeted unless user points `DATABASE_URL` there.

## Primary Files in New App

- `apps/pipeline/src/pipeline/cli.py`
- `apps/pipeline/src/pipeline/migrator.py`
- `apps/pipeline/src/pipeline/sql/migrations/*`
- `apps/pipeline/PIPELINE_PLAN.md`
