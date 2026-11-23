"""Write tests/fixtures/contract/openapi.json: the API contract as the code generates it.

    PYTHONPATH=. python scripts/write_openapi_snapshot.py

The contract test fails when the generated spec differs from this file. Run this script only when
a change to a route, a request or a response is meant, and commit the result with the change.
"""

from __future__ import annotations

import json
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "contract" / "openapi.json"


def current_spec() -> dict:
    from app.main import app

    return app.openapi()


def render(spec: dict) -> str:
    return json.dumps(spec, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def main() -> None:
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(render(current_spec()), encoding="utf-8", newline="\n")
    print(f"wrote {SNAPSHOT}")


if __name__ == "__main__":
    main()
