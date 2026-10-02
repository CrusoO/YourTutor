from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.content.loader import LoadError, load_path
from app.content.validator import validate_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.content")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("root", type=Path)
    load = sub.add_parser("load")
    load.add_argument("root", type=Path)
    load.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)

    if args.command == "validate":
        report = validate_path(args.root)
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        if report.errors:
            for error in report.errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        bundle = report.bundle
        assert bundle is not None
        print(
            f"OK: {len(bundle.skills)} skills, {len(bundle.items)} items, "
            f"{len(bundle.misconceptions)} misconceptions, {len(bundle.overlays)} overlays"
        )
        return 0

    try:
        report = load_path(args.root, database_url=args.database_url)
    except LoadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    print("Loaded content.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
