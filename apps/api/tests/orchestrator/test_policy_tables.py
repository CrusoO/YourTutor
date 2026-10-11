"""The shared policy tables (transitions, encouragement variants) match the Python source."""

from __future__ import annotations

import json

from scripts.write_policy_tables import tables, target


def test_the_committed_policy_tables_are_up_to_date() -> None:
    committed = json.loads(target().read_text(encoding="utf-8"))
    assert committed == tables(), "run: PYTHONPATH=. python scripts/write_policy_tables.py"
