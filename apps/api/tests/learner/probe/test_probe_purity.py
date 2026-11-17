"""The probe is pure: no database, settings, orchestrator, randomness, clock or logging."""

from __future__ import annotations

import ast
from pathlib import Path

import app.learner.probe as probe_pkg

FORBIDDEN = ("app.db", "app.config", "app.orchestrator", "random", "time", "datetime", "logging")
PACKAGE_DIR = Path(probe_pkg.__file__).parent


def imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def test_no_module_imports_a_forbidden_package() -> None:
    files = sorted(PACKAGE_DIR.glob("*.py"))
    assert len(files) >= 9
    for path in files:
        for module in imported_modules(path.read_text(encoding="utf-8")):
            for banned in FORBIDDEN:
                assert module != banned and not module.startswith(banned + "."), (
                    f"{path.name} imports {module}"
                )


def test_only_the_config_loader_touches_the_file_system() -> None:
    for path in sorted(PACKAGE_DIR.glob("*.py")):
        if path.name == "config.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "open(" not in source and "pathlib" not in source, path.name


def test_every_module_is_under_250_lines() -> None:
    for path in sorted(PACKAGE_DIR.glob("*.py")):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 250, path.name
