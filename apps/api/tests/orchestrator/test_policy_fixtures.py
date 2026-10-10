"""The golden policy sessions the offline TypeScript policy must reproduce.

The committed files must equal what the Python policy produces now, so changing the policy
without re-recording them (and re-checking the TypeScript mirror) fails here.
"""

from __future__ import annotations

import json

import pytest

from scripts.write_policy_fixtures import OUT, scenarios

RECORDED = {
    path.name: json.loads(path.read_text(encoding="utf-8")) for path in sorted(OUT.glob("*.json"))
}
NOW = scenarios()


def test_there_are_scenarios_for_the_main_rules() -> None:
    names = " ".join(RECORDED)
    for needle in ("lesson_flow", "stuck", "slip", "probe", "frustration", "stretch", "warmup"):
        assert needle in names
    assert len(RECORDED) >= 20


@pytest.mark.parametrize("index", range(len(NOW)))
def test_the_committed_scenario_matches_the_python_policy(index: int) -> None:
    fresh = json.loads(json.dumps(NOW[index], ensure_ascii=False))
    name = f"{index + 1:02d}_{fresh['name']}.json"
    assert RECORDED[name] == fresh, "run: PYTHONPATH=. python scripts/write_policy_fixtures.py"
