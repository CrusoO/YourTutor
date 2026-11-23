"""The API contract does not change by accident.

A refactor must leave every route, request and response as it was. If this test fails after a change
that was meant to alter the API, regenerate the snapshot (scripts/write_openapi_snapshot.py) and
commit it with the change, so a reviewer sees the contract diff.
"""

from __future__ import annotations

import json

from scripts.write_openapi_snapshot import SNAPSHOT, current_spec, render


def test_the_generated_spec_matches_the_committed_snapshot() -> None:
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    actual = json.loads(render(current_spec()))
    if actual == expected:
        return
    old, new = set(expected["paths"]), set(actual["paths"])
    changed = sorted(p for p in old & new if expected["paths"][p] != actual["paths"][p])
    raise AssertionError(
        "the API contract changed. "
        f"added routes: {sorted(new - old)}; removed routes: {sorted(old - new)}; "
        f"changed routes: {changed}; "
        f"schemas differ: {expected['components'] != actual['components']}. "
        "If this is meant, run `PYTHONPATH=. python scripts/write_openapi_snapshot.py` and commit."
    )


def test_every_route_has_a_unique_operation_id() -> None:
    ids = [
        op["operationId"]
        for methods in current_spec()["paths"].values()
        for op in methods.values()
        if isinstance(op, dict) and "operationId" in op
    ]
    assert len(ids) == len(set(ids))
