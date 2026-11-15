"""The trusted kernel stays small, stdlib-only and independent of the rest of the app."""

import ast
import sys
from pathlib import Path

KERNEL = Path(__file__).resolve().parents[2] / "app" / "factory" / "kernel"
STDLIB = set(sys.stdlib_module_names)


def test_kernel_imports_only_stdlib_and_itself():
    for path in KERNEL.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            for name in names:
                root = name.split(".")[0]
                ok = root in STDLIB or name.startswith("app.factory.kernel")
                assert ok, f"{path.name} imports {name}: the kernel may not depend on it"


def test_kernel_size_budget():
    lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in KERNEL.glob("*.py"))
    assert lines < 1500, f"kernel is {lines} lines; the budget is 1,500 so one person can review it"


def test_no_float_arithmetic_in_the_kernel():
    for path in KERNEL.glob("*.py"):
        if path.name == "certify.py":  # the statistical bound uses math.log and floats on purpose
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        floats = [
            n.lineno
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, float)
        ]
        assert not floats, f"{path.name} has float literals at {floats}"
