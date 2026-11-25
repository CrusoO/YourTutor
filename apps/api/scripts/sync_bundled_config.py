"""Copy `<repo>/config` into `apps/api/bundled_config` (Vercel uploads only `apps/api`).

Run after changing anything under `config/`:  python scripts/sync_bundled_config.py
`tests/test_bundled_config.py` fails when the two folders differ.
"""

from __future__ import annotations

import shutil
from pathlib import Path

API = Path(__file__).resolve().parents[1]
SOURCE = API.parents[1] / "config"
TARGET = API / "bundled_config"


def main() -> None:
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir()
    for path in sorted(SOURCE.rglob("*")):
        if path.is_file():
            out = TARGET / path.relative_to(SOURCE)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    print(f"copied {sum(1 for p in TARGET.rglob('*') if p.is_file())} files")


if __name__ == "__main__":
    main()
