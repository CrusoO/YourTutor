"""Write apps/api/app/content_review/review_snapshot.json.gz: the validated items, misconception
titles, Hindi strings and chapter map the review routes read, so a short-lived serverless function
need not parse about 2,300 YAML files on every cold start.

    PYTHONPATH=. python scripts/write_review_snapshot.py

Run it whenever content under content/ changes (items, misconceptions, overlays, curriculum) and
commit the result; `tests/content_review/test_snapshot.py` fails when the committed file is stale.
"""

from __future__ import annotations

from app.content_review import snapshot
from app.registries.paths import content_root


def main() -> None:
    data = snapshot.build(content_root())
    snapshot.write(snapshot.SNAPSHOT_PATH, data)
    size = snapshot.SNAPSHOT_PATH.stat().st_size
    print(f"wrote {snapshot.SNAPSHOT_PATH} ({len(data['items'])} items, {size} bytes)")


if __name__ == "__main__":
    main()
