"""Copy `config/` and `content/curricula/` into `apps/api` (Vercel uploads only `apps/api`).

Run after changing anything under those two folders:  python scripts/sync_bundled_config.py
`tests/test_bundled_config.py` fails when a copy differs from its source.
"""

from __future__ import annotations

import shutil
from pathlib import Path

API = Path(__file__).resolve().parents[1]
COPIES = {
    API.parents[1] / "config": API / "bundled_config",
    API.parents[1] / "content" / "curricula": API / "bundled_curricula",
}


def main() -> None:
    for source, target in COPIES.items():
        if target.exists():
            shutil.rmtree(target)
        target.mkdir()
        for path in sorted(source.rglob("*")):
            if path.is_file():
                out = target / path.relative_to(source)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        print(f"{target.name}: {sum(1 for p in target.rglob('*') if p.is_file())} files")


if __name__ == "__main__":
    main()
