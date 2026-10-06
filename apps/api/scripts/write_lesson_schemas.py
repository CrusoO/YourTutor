"""Regenerate packages/shared/schemas/*.schema.json from the Pydantic models.

Run from apps/api: `PYTHONPATH=. python scripts/write_lesson_schemas.py`. A test fails when the
committed files drift from the models.
"""

from __future__ import annotations

import json

from app.lessons.schema import lesson_json_schemas
from app.registries.paths import repo_root


def main() -> None:
    out = repo_root() / "packages" / "shared" / "schemas"
    out.mkdir(parents=True, exist_ok=True)
    for name, schema in lesson_json_schemas().items():
        (out / name).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out / name}")


if __name__ == "__main__":
    main()
