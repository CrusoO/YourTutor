"""Hardening: no dynamic code execution in app/ outside an explicit, reviewed allowlist."""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
BARE_FORBIDDEN = {"eval", "exec", "compile", "__import__", "sympify", "parse_expr"}
METHOD_FORBIDDEN = {"eval", "exec", "sympify", "parse_expr"}  # re.compile and friends are fine
# Every entry is a reviewed place where text becomes code, with the guard that protects it.
ALLOWED = {
    # guards: allowlist regex, length and bracket limits, empty __builtins__ (test_parse_safety)
    ("content/math_parse.py", "parse_expr"),
}


def _calls(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BARE_FORBIDDEN:
                names.add(func.id)
            elif isinstance(func, ast.Attribute) and func.attr in METHOD_FORBIDDEN:
                names.add(func.attr)
    return names


def test_eval_exec_and_sympify_appear_only_where_reviewed() -> None:
    found = {
        (path.relative_to(APP).as_posix(), name)
        for path in APP.rglob("*.py")
        for name in _calls(path)
    }
    assert found <= ALLOWED, f"unreviewed dynamic execution: {sorted(found - ALLOWED)}"


def test_the_allowlist_has_no_stale_entries() -> None:
    found = {
        (path.relative_to(APP).as_posix(), name)
        for path in APP.rglob("*.py")
        for name in _calls(path)
    }
    assert ALLOWED <= found
