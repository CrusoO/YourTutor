"""`python -m app.authoring lint|compile|report` (run from apps/api, never from apps/api/app)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from app.authoring.compile import (
    Compiled,
    authored_files,
    compile_draft,
    write_compiled,
)
from app.authoring.lint import LintRun, lint_paths
from app.authoring.report import build_report


def default_content_root() -> Path:
    override = os.environ.get("CONTENT_DIR")
    return Path(override) if override else Path(__file__).resolve().parents[4] / "content"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.authoring")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("lint", "check draft files with deterministic rules (exit 1 on any error)"),
        ("compile", "lint, then write Item, skill and misconception YAML at tier C draft"),
        ("report", "counts per class, subject, chapter and topic against the target of 6"),
    ):
        cmd = sub.add_parser(name, help=text)
        cmd.add_argument("--content-root", type=Path, default=None)
        cmd.add_argument("--json", action="store_true", help="machine-readable output")
        if name != "report":
            cmd.add_argument("files", nargs="*", type=Path, help="draft files (default: all)")
    sub.choices["compile"].add_argument(
        "--clean", action="store_true", help="delete authored output no draft produces any more"
    )
    sub.choices["compile"].add_argument(
        "--dry-run", action="store_true", help="lint and compile in memory, write nothing"
    )
    sub.choices["lint"].add_argument(
        "--out", type=Path, default=None, help="also write the report to this file"
    )
    return parser


def _emit(run: LintRun, as_json: bool) -> str:
    return json.dumps(run.to_json(), indent=2, ensure_ascii=False) if as_json else run.to_text()


def _compile(args: argparse.Namespace, root: Path) -> int:
    run = lint_paths(root, args.files or None)
    merged = Compiled()
    for result in run.files:
        if result.draft is None or result.file_blocked:
            continue
        one = compile_draft(result.draft, result.topics, result.bad_items())
        merged.files.update(one.files)
        merged.items += one.items
        merged.skills += one.skills
        merged.misconceptions += one.misconceptions
        merged.short_topics.extend(one.short_topics)
    print(_emit(run, args.json), file=sys.stderr if args.json else sys.stdout)
    removed = 0
    changed = 0
    if not args.dry_run:
        changed = write_compiled(root, merged)
        if args.clean:
            for rel in sorted(authored_files(root) - set(merged.files)):
                (root / rel).unlink()
                removed += 1
    summary = {
        "items": merged.items,
        "skills": merged.skills,
        "misconceptions": merged.misconceptions,
        "files_changed": changed,
        "files_removed": removed,
        "topics_left_out_under_5_items": merged.short_topics,
        "skipped_files": sum(1 for r in run.files if r.file_blocked),
        "lint_errors": run.error_count,
        "dry_run": bool(args.dry_run),
    }
    print(
        json.dumps(summary)
        if args.json
        else "compiled " + ", ".join(f"{k}={v}" for k, v in summary.items())
    )
    return 1 if run.error_count else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = (args.content_root or default_content_root()).resolve()
    if args.command == "report":
        report = build_report(root)
        print(json.dumps(report.to_json(), indent=2) if args.json else report.to_text())
        return 0
    if args.command == "lint":
        run = lint_paths(root, args.files or None)
        text = _emit(run, args.json)
        print(text)
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text + "\n")
        return 1 if run.error_count else 0
    return _compile(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
