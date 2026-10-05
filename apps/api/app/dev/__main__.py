"""`python -m app.dev seed_scenarios` — dev-only preview data."""

from __future__ import annotations

import argparse
import sys

from app.dev.scenarios import seed_scenarios


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.dev")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed_scenarios", help="create preview students by replaying events")
    seed.add_argument("--database-url", default=None)
    seed.add_argument("--only", action="append", help="scenario name (repeatable)")
    args = parser.parse_args(argv)
    try:
        report = seed_scenarios(args.database_url, only=args.only)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{'scenario':<22} {'family code':<12} {'PIN':<6} state")
    for row in report:
        print(f"{row['name']:<22} {row['family_code']:<12} {row['pin']:<6} {row['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
