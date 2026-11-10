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


def _content_root(root: Path | None) -> Path:
    from app.registries.paths import content_root

    return root or content_root()


def _rights_command(args: argparse.Namespace) -> int:
    if args.command == "blueprint-import":
        from app.content.blueprint import import_csv

        imported = import_csv(
            args.csv, _content_root(args.root), source_deleted=args.source_deleted == "true"
        )
        if not imported.ok:
            for message in imported.errors:
                print(f"ERROR: {message}", file=sys.stderr)
            print("Nothing was imported.", file=sys.stderr)
            return 1
        assert imported.audit is not None
        print(
            f"Imported {imported.added} rows from {imported.audit['source_file']} "
            f"(sha256 {imported.audit['sha256']}, source_deleted={args.source_deleted})"
        )
        return 0
    if args.command == "blueprint-report":
        from app.content.blueprint import format_report as blueprint_report
        from app.content.blueprint import load_blueprint

        print(blueprint_report(load_blueprint(_content_root(args.root))))
        return 0
    if args.command == "originality-index":
        from app.content.originality import build_index

        if not args.source.is_dir():
            print(f"ERROR: {args.source} is not a folder", file=sys.stderr)
            return 1
        index, files = build_index(args.source)
        args.out.write_text(index.to_json(), encoding="utf-8")
        print(
            f"Indexed {files} files, {index.units} units, {len(index.shingle_hashes)} hashes "
            f"-> {args.out} (hashes only)"
        )
        return 0
    from app.content.originality import ReferenceIndex, item_text, score_text
    from app.content.validator import load_bundle

    index = ReferenceIndex.from_json(args.index.read_text(encoding="utf-8"))
    bundle = load_bundle(_content_root(args.root))
    counts: dict[str, int] = {"pass": 0, "review": 0, "block": 0}
    for item in bundle.items:
        score = score_text(item_text(item.stem.en, (o.en for o in item.options)), index)
        counts[score.status.value] += 1
        print(
            f"{score.status.value:6} {item.id} containment={score.containment:.2f} "
            f"run={score.longest_run} structure={'match' if score.structure_match else 'no'}"
        )
    print(f"pass {counts['pass']}, review {counts['review']}, block {counts['block']}")
    return 1 if counts["block"] else 0


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
    apply = sub.add_parser(
        "apply-reviews",
        help="Write approvals from the review screen (2 distinct approvals on the current hash).",
    )
    apply.add_argument("root", type=Path)
    apply.add_argument("--database-url", default=None)
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
    bp_import = sub.add_parser(
        "blueprint-import",
        help="Import a hand-filled facts-only CSV of past-paper rows into content/blueprint.",
    )
    bp_import.add_argument("csv", type=Path)
    bp_import.add_argument("--root", type=Path, default=None)
    bp_import.add_argument(
        "--source-deleted",
        choices=["true", "false"],
        default="false",
        help="Record in the audit log whether the source file has been deleted.",
    )
    bp_report = sub.add_parser(
        "blueprint-report", help="Marks by chapter and type per year, and year-on-year drift."
    )
    bp_report.add_argument("--root", type=Path, default=None)
    orig_index = sub.add_parser(
        "originality-index",
        help="Read local reference files and write a file of hashes only (never text).",
    )
    orig_index.add_argument("--from", dest="source", type=Path, required=True)
    orig_index.add_argument("--out", type=Path, required=True)
    orig_check = sub.add_parser(
        "originality-check", help="Score the bank's items against a hash index: pass/review/block."
    )
    orig_check.add_argument("--index", type=Path, required=True)
    orig_check.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command in {
        "blueprint-import",
        "blueprint-report",
        "originality-index",
        "originality-check",
    }:
        return _rights_command(args)

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

    if args.command == "apply-reviews":
        from app.content_review.apply import apply_reviews
        from app.db.session import session_factory

        with session_factory(args.database_url)() as session:
            applied = apply_reviews(session, args.root)
        print(f"Approved: {len(applied.approved)}")
        for approved_id in applied.approved:
            print(f"  {approved_id}")
        print(f"Waiting for a second approval: {len(applied.waiting)}")
        print(f"Blocked by a reject or fix: {len(applied.blocked)}")
        if applied.refused:
            print("Refused (failed validation): " + ", ".join(applied.refused), file=sys.stderr)
        return 1 if applied.refused else 0

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
