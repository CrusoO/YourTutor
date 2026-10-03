from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ALLOWLIST_PREFIXES = (
    "config/",
    "content/",
    "apps/api/migrations/",
    "apps/api/tests/",
    "apps/api/scripts/generate_seed.py",
    "apps/api/scripts/write_e2e_mini_content.py",
    "apps/web/e2e/",
    "apps/web/lib/dev-auth.ts",
    "packages/shared/fixtures/",
)
SKIP_PATH_PARTS = ("node_modules", ".next", "check_region_literals.py")

IANA = re.compile(r"\b(Asia|Europe|America|Africa|Australia|Pacific)/[A-Za-z_]+")
BOARD_NAMES = re.compile(r"\b(bhutan|seba)\b", re.IGNORECASE)
SCAN_SUFFIXES = {".py", ".ts", ".tsx"}


def _allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if any(part in SKIP_PATH_PARTS for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if _allowed(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in (IANA, BOARD_NAMES):
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{rel}:{line}: {match.group(0)}")
    if violations:
        print("Region literal violations:", file=sys.stderr)
        for row in violations:
            print(row, file=sys.stderr)
        return 1
    print("OK: no region literals outside allowlist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
