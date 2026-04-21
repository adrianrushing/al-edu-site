from __future__ import annotations

import argparse

REMOVED_COMMANDS = (
    "status",
    "plan",
    "apply",
    "manifest",
    "sources",
    "ingest-bronze",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Legacy pipeline CLI (medallion architecture removed)"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        help="Former command name for compatibility",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command in REMOVED_COMMANDS:
        print(
            f"Command '{args.command}' was removed because the medallion architecture "
            "was retired."
        )
        return 1

    print("All medallion pipeline commands have been removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
