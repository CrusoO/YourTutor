"""Imports between app packages only get fewer (a ratchet), and the foundation stays at the bottom.

import_baseline.json lists every package-to-package import that exists today. A new one fails this
test: either the code does not need it, or it is a design decision to make in review. A listed one
that no longer exists also fails, so the list shrinks as the code is untangled
(PYTHONPATH=. python -m tests.architecture.write_import_baseline).
"""

from __future__ import annotations

import json

from tests.architecture.graph import package_edges
from tests.architecture.write_import_baseline import BASELINE

# These must import nothing from the rest of the app: everything else depends on them.
# (safety is not here: it is a feature package and imports ask, auth, helplines and others.)
FOUNDATION = {"config": set(), "db": {"config"}}


def _baseline() -> set[tuple[str, str]]:
    return {tuple(line.split(" -> ")) for line in json.loads(BASELINE.read_text(encoding="utf-8"))}  # type: ignore[misc]


def test_no_new_import_between_packages() -> None:
    new = sorted(package_edges() - _baseline())
    assert not new, (
        f"new imports between app packages: {new}. Remove them, or discuss the dependency in "
        "review and add it to tests/architecture/import_baseline.json by hand, with the reason "
        "in the PR."
    )


def test_every_baseline_entry_still_exists() -> None:
    gone = sorted(_baseline() - package_edges())
    assert not gone, (
        f"these imports are gone: {gone}. Good: run "
        "`PYTHONPATH=. python -m tests.architecture.write_import_baseline` "
        "and commit the shorter list."
    )


def test_the_foundation_imports_nothing_above_it() -> None:
    for unit, allowed in FOUNDATION.items():
        imported = {b for a, b in package_edges() if a == unit}
        assert imported <= allowed, f"{unit} imports {sorted(imported - allowed)}"


def test_the_ratchet_catches_a_new_import_and_a_removed_one(monkeypatch) -> None:  # noqa: ANN001
    real = package_edges()
    monkeypatch.setattr(
        "tests.architecture.test_import_boundaries.package_edges",
        lambda: real | {("config", "auth")},
    )
    try:
        test_no_new_import_between_packages()
        raise RuntimeError("a new import was not caught")
    except AssertionError as err:
        assert "config" in str(err) and "auth" in str(err)
    monkeypatch.setattr(
        "tests.architecture.test_import_boundaries.package_edges",
        lambda: set(sorted(real)[1:]),
    )
    try:
        test_every_baseline_entry_still_exists()
        raise RuntimeError("a removed import was not caught")
    except AssertionError as err:
        assert "gone" in str(err)
