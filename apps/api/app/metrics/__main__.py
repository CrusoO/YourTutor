import json
import sys

from app.db.session import session_factory
from app.metrics.pilot import pilot_metrics


def main(argv: list[str]) -> int:
    if argv != ["pilot"]:
        print("usage: python -m app.metrics pilot", file=sys.stderr)
        return 2
    with session_factory()() as db:
        print(json.dumps(pilot_metrics(db), indent=2))
    return 0


raise SystemExit(main(sys.argv[1:]))
