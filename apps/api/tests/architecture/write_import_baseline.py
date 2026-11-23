"""Rewrite import_baseline.json from the code.

    PYTHONPATH=. python -m tests.architecture.write_import_baseline

Run it only after REMOVING an import between packages (the ratchet test tells you when). Never run
it to allow a new import: that is a design decision, made in a pull request a reviewer can see.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.architecture.graph import package_edges

BASELINE = Path(__file__).with_name("import_baseline.json")


def main() -> None:
    edges = sorted(f"{a} -> {b}" for a, b in package_edges())
    BASELINE.write_text(json.dumps(edges, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(edges)} edges to {BASELINE}")


if __name__ == "__main__":
    main()
