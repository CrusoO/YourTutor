"""Which app package imports which. Read from the source with `ast`, so nothing is executed.

A unit is the first name under `app/`: a package (`app/auth/...`) or a top-level module
(`app/config.py` is `config`). Imports inside functions count: a lazy import is still a dependency.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
ROOT_OF_COMPOSITION = {"main"}  # the app wires every router together, so it may import anything


def unit_of(path: Path) -> str:
    first = path.relative_to(APP).parts[0]
    return first[:-3] if first.endswith(".py") else first


def package_edges() -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for path in APP.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        source = unit_of(path)
        if source in ROOT_OF_COMPOSITION:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            for name in names:
                parts = name.split(".")
                if parts[0] == "app" and len(parts) > 1 and parts[1] != source:
                    edges.add((source, parts[1]))
    return edges
