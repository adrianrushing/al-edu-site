from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineManifest:
    version: str
    steps: list[dict[str, object]]


def load_manifest(manifest_path: Path | None = None) -> PipelineManifest:
    path = manifest_path or (
        Path(__file__).resolve().parent / "sql" / "specs" / "etl_steps.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PipelineManifest(version=str(payload["version"]), steps=list(payload["steps"]))
