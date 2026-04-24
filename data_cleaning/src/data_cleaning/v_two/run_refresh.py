from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run_cmd(command: list[str], env: dict[str, str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, env=env, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight sandbox/core refresh")
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--repo-root",
        default=str(Path.cwd()),
        help="Repository root path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    env = os.environ.copy()
    env["DATABASE_URL"] = args.database_url

    impute_script = repo_root / "data_cleaning/src/data_cleaning/v_two/impute_student_demographics_light.py"
    sandbox_sql = repo_root / "data_cleaning/src/data_cleaning/v_two/sandbox_refresh_all_review.sql"
    core_sql = repo_root / "data_cleaning/src/data_cleaning/v_two/core_load_review_to_core.sql"
    validate_sql = repo_root / "data_cleaning/src/data_cleaning/v_two/validate_refresh.sql"

    run_cmd(
        [
            "uv",
            "run",
            "--project",
            "data_cleaning",
            "python",
            str(impute_script),
            "--db-uri",
            args.database_url,
        ],
        env=env,
    )

    run_cmd(
        [
            "psql",
            args.database_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(sandbox_sql),
        ],
        env=env,
    )

    run_cmd(
        [
            "psql",
            args.database_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(core_sql),
        ],
        env=env,
    )

    run_cmd(
        [
            "psql",
            args.database_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(validate_sql),
        ],
        env=env,
    )


if __name__ == "__main__":
    main()
