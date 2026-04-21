# EFLT Pipeline (Legacy)

The medallion architecture components (`bronze`, `silver`, `platinum`, and
`pipeline_meta`) have been removed from this repository.

The `pipeline` package is kept only as a compatibility placeholder so the
existing project layout and script entry point remain valid.

Running the CLI now reports that the medallion commands were removed:

```bash
uv run --project apps/pipeline python -m pipeline.cli
```
