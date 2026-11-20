import argparse
import json
import sys
from datetime import date

from app.db.session import session_factory
from app.metrics.baseline import baseline_metrics, render_table
from app.metrics.pilot import pilot_metrics


def _baseline(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.metrics baseline")
    parser.add_argument("--since", required=True, type=date.fromisoformat)
    parser.add_argument("--until", required=True, type=date.fromisoformat)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.until < args.since:
        print("--until must not be before --since", file=sys.stderr)
        return 2
    with session_factory()() as db:
        report = baseline_metrics(db, args.since, args.until)
    print(json.dumps(report, indent=2) if args.json else render_table(report))
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["baseline"]:
        return _baseline(argv[1:])
    if argv != ["pilot"]:
        print(
            "usage: python -m app.metrics pilot | baseline --since YYYY-MM-DD "
            "--until YYYY-MM-DD [--json]",
            file=sys.stderr,
        )
        return 2
    with session_factory()() as db:
        print(json.dumps(pilot_metrics(db), indent=2))
    return 0


raise SystemExit(main(sys.argv[1:]))
