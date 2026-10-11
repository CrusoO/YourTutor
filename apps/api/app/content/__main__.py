from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.content.coverage import format_coverage
from app.content.generate import generate_from_templates
from app.content.loader import LoadError, PruneBlockedError, load_path
from app.content.locale_review import export_locale_review, import_locale_review, locale_report
from app.content.review import export_sheet, import_sheet_report
from app.content.validator import format_report, validate_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.content")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("root", type=Path)
    load = sub.add_parser("load")
    load.add_argument("root", type=Path)
    load.add_argument("--database-url", default=None)
    load.add_argument(
        "--prune",
        action="store_true",
        help=(
            "Hard-delete skills/items absent from the bundle (refuses if learner data references "
            "them)."
        ),
    )
    export = sub.add_parser("export-review")
    export.add_argument("root", type=Path)
    export.add_argument("--csv", type=Path, required=True)
    export.add_argument("--html", type=Path, required=True)
    imported = sub.add_parser("import-review")
    imported.add_argument("csv", type=Path)
    imported.add_argument("root", type=Path)
    imported.add_argument("--reviewer", required=True)
    coverage = sub.add_parser("coverage")
    coverage.add_argument("root", type=Path)
    loc_export = sub.add_parser("export-locale-review")
    loc_export.add_argument("root", type=Path)
    loc_export.add_argument("--locale", required=True)
    loc_export.add_argument("--csv", type=Path, required=True)
    loc_import = sub.add_parser("import-locale-review")
    loc_import.add_argument("csv", type=Path)
    loc_import.add_argument("root", type=Path)
    loc_import.add_argument("--locale", required=True)
    loc_import.add_argument("--reviewer", required=True)
    loc_status = sub.add_parser("locale-status")
    loc_status.add_argument("root", type=Path)
    loc_status.add_argument("--locale", required=True)
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
    if args.command == "coverage":
        found = validate_path(args.root)
        if found.bundle is None:
            print("; ".join(found.errors), file=sys.stderr)
            return 1
        print(format_coverage(found.bundle.templates, found.bundle.items))
        return 0

    if args.command == "export-locale-review":
        count = export_locale_review(args.root, args.locale, args.csv)
        print(f"{count} strings to review in {args.locale}: {args.csv}")
        return 0

    if args.command == "import-locale-review":
        loc_result = import_locale_review(args.csv, args.root, args.locale, args.reviewer)
        print(f"Approved {len(loc_result.approved)} strings")
        for reason in loc_result.refused:
            print(f"Refused {reason}")
        return 1 if loc_result.refused else 0

    if args.command == "locale-status":
        counts = locale_report(args.root, args.locale)
        print(", ".join(f"{key}: {value}" for key, value in counts.items()))
        return 0

    if args.command == "import-review":
        result = import_sheet_report(args.csv, args.root, args.reviewer)
        print("Approved: " + ", ".join(result.approved))
        if result.stale:
            print("Stale (changed since export, export again): " + ", ".join(result.stale))
        if result.refused:
            print("Refused (unknown or failed validation): " + ", ".join(result.refused))
        return 1 if result.stale or result.refused else 0

    try:
        from app.content.bundle_merge import e2e_mini_enabled

        report = load_path(
            args.root,
            database_url=args.database_url,
            include_e2e_mini=e2e_mini_enabled(),
            prune=args.prune,
        )
    except PruneBlockedError as exc:
        for reason in exc.reasons:
            print(f"ERROR: {reason}", file=sys.stderr)
        return 1
    except LoadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    print("Loaded content.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
