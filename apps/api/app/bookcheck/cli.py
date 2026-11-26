"""Command line: python -m app.bookcheck <command>. Console output is counts and OUR keys only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.bookcheck import check, coverage, facts, ingest, overlap, report, toc
from app.bookcheck.items import discover_scopes
from app.bookcheck.settings import (
    CLASSES,
    SUBJECTS,
    Settings,
    SettingsError,
    find_repo_root,
    load_settings,
)


def _default_content_root() -> Path:
    root = find_repo_root()
    return (root or Path.cwd()) / "content"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.bookcheck", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create the folder skeleton")
    sub.add_parser("ingest", help="extract and cache the text of every PDF")
    sub.add_parser("toc", help="detect chapters and sections")
    sub.add_parser("facts", help="extract constants, formulas and defined terms")
    sub.add_parser("report", help="write the private report")

    def scope(p: argparse.ArgumentParser, required: bool) -> None:
        p.add_argument("--class", dest="grade", type=int, choices=CLASSES, required=required)
        p.add_argument("--subject", choices=SUBJECTS, required=required)
        p.add_argument("--content-root", type=Path, default=None)

    cov = sub.add_parser("coverage", help="match book headings to our syllabus map")
    scope(cov, True)
    chk = sub.add_parser("check", help="compare our items with the books")
    scope(chk, True)
    chk.add_argument("--items", choices=("drafts", "compiled", "all"), default="all")
    ovl = sub.add_parser("overlap", help="copy detector (exit 1 when a copy is found)")
    scope(ovl, False)
    ovl.add_argument("--n", type=int, default=overlap.DEFAULT_N)
    ovl.add_argument("--all-books", action="store_true")
    run = sub.add_parser("run-all", help="ingest, toc, coverage, facts, check, overlap for a class")
    run.add_argument("--class", dest="grade", type=int, choices=CLASSES, required=True)
    run.add_argument("--content-root", type=Path, default=None)
    run.add_argument("--n", type=int, default=overlap.DEFAULT_N)
    return parser


def _say(text: str) -> None:
    print(text)


def _print_counts(label: str, counts: dict[str, int]) -> None:
    _say(f"{label}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


def _coverage_summary(grade: int, subject: str, summary: dict | None) -> None:
    if summary is None:
        _say(f"coverage {grade}-{subject}: no syllabus map found")
        return
    _say(f"coverage {grade}-{subject}: {summary['headings']} book headings")
    for key in ("topics_without_match", "chapters_low_match"):
        _say(f"  {key}: {', '.join(summary[key]) or 'none'}")
    _say(f"  unmatched_book_headings: {summary['unmatched_book_headings']}")
    _say(
        "  low_confidence_chapters_with_match: "
        f"{', '.join(summary['low_confidence_chapters_matched']) or 'none'}"
    )
    _say(
        "  low_confidence_chapters_without_match: "
        f"{', '.join(summary['low_confidence_chapters_unmatched']) or 'none'}"
    )


def _check(settings: Settings, root: Path, grade: int, subject: str, which: str) -> None:
    counts = check.run_check(settings, root, grade, subject, which)
    if counts is None:
        _say(f"check {grade}-{subject}: no book for this class and subject")
    else:
        _print_counts(f"check {grade}-{subject}", counts)


def _overlap(
    settings: Settings, root: Path, scopes: list[tuple[int, str]], n: int, all_books: bool
) -> int:
    result = overlap.run_overlap(settings, root, scopes, n, all_books)
    _say(
        f"overlap (n={n}): scopes_checked={result['scopes_checked']}, "
        f"scopes_without_books={result['no_books']}, items={result['items']}, "
        f"flagged_items={len(result['flagged_items'])}"
    )
    for item_id in result["flagged_items"]:
        _say(f"  copy suspected in our item: {item_id}")
    return 1 if result["flagged_items"] else 0


def _run_all(settings: Settings, root: Path, grade: int, n: int) -> int:
    _print_counts("ingest", ingest.ingest(settings))
    _print_counts("toc", toc.run_toc(settings))
    _print_counts("facts", facts.run_facts(settings))
    scopes = []
    for subject in SUBJECTS:
        if subject == "science":
            continue
        _coverage_summary(grade, subject, coverage.run_coverage(settings, root, grade, subject))
        _check(settings, root, grade, subject, "all")
        scopes.append((grade, subject))
    code = _overlap(settings, root, scopes, n, False)
    _print_counts("report", report.build_report(settings))
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = load_settings()
    except SettingsError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 2
    root = getattr(args, "content_root", None) or _default_content_root()
    try:
        match args.command:
            case "init":
                for line in ingest.init(settings):
                    _say(line)
            case "ingest":
                _print_counts("ingest", ingest.ingest(settings))
            case "toc":
                _print_counts("toc", toc.run_toc(settings))
            case "facts":
                _print_counts("facts", facts.run_facts(settings))
            case "coverage":
                _coverage_summary(
                    args.grade,
                    args.subject,
                    coverage.run_coverage(settings, root, args.grade, args.subject),
                )
            case "check":
                _check(settings, root, args.grade, args.subject, args.items)
            case "overlap":
                if args.grade and args.subject:
                    scopes = [(args.grade, args.subject)]
                else:
                    scopes = [
                        s
                        for s in discover_scopes(root)
                        if (not args.grade or s[0] == args.grade)
                        and (not args.subject or s[1] == args.subject)
                    ]
                return _overlap(settings, root, scopes, args.n, args.all_books)
            case "report":
                _print_counts("report", report.build_report(settings))
                _say("private report written to the output folder")
            case "run-all":
                return _run_all(settings, root, args.grade, args.n)
    except ingest.PypdfMissing as err:
        print(str(err), file=sys.stderr)
        return 2
    return 0
