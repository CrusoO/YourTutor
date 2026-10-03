from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.content.generate import generate_from_templates
from app.content.loader import LoadError, load_path
from app.content.review import export_sheet, import_sheet
from app.content.validator import format_report, validate_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.content")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("root", type=Path)
    load = sub.add_parser("load")
    load.add_argument("root", type=Path)
    load.add_argument("--database-url", default=None)
    export = sub.add_parser("export-review")
    export.add_argument("root", type=Path)
    export.add_argument("--csv", type=Path, required=True)
    export.add_argument("--html", type=Path, required=True)
    imported = sub.add_parser("import-review")
    imported.add_argument("csv", type=Path)
    imported.add_argument("root", type=Path)
    imported.add_argument("--reviewer", required=True)
    generate = sub.add_parser("generate-from-templates")
    generate.add_argument("root", type=Path)
    generate.add_argument("--seed", type=int, default=42)
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
        print(format_report(report))
        print(
            f"OK: {len(bundle.skills)} skills, {len(bundle.items)} items, "
            f"{len(bundle.misconceptions)} misconceptions, {len(bundle.overlays)} overlays"
        )
        return 0

    if args.command == "generate-from-templates":
        items = generate_from_templates(args.root, seed=args.seed)
        print(f"Generated {len(items)} practice instances (seed={args.seed})")
        report = validate_path(args.root)
        print(format_report(report))
        if report.errors:
            for error in report.errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        return 0
    if args.command == "export-review":
        count = export_sheet(args.root, args.csv, args.html)
        print(f"Exported {count} items")
        return 0
    if args.command == "import-review":
        approved = import_sheet(args.csv, args.root, args.reviewer)
        print("Approved: " + ", ".join(approved))
        return 0

    try:
        from app.content.bundle_merge import e2e_mini_enabled

        report = load_path(
            args.root,
            database_url=args.database_url,
            include_e2e_mini=e2e_mini_enabled(),
        )
    except LoadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    print("Loaded content.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
