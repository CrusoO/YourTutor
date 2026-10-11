from __future__ import annotations

import json

from app.lessons.path import lesson_path
from app.registries.paths import repo_root

FIXTURE = repo_root() / "packages" / "shared" / "fixtures" / "lesson_path" / "cases.json"


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_lesson_path_fixture_cases() -> None:
    data = _load()
    for case in data["cases"]:
        beats = case.get("beats", data["beats"])
        order, serve = lesson_path(case["prerequisite_levels"], beats)
        assert order == case["order"], case["name"]
        assert serve == case["serve"], case["name"]


def test_lesson_path_never_drops_the_first_or_last_beat() -> None:
    for levels in ([], [0], [3], [4], [7]):
        _, serve = lesson_path(
            levels, ["predict", "explore", "explain_scene", "worked_example", "check"]
        )
        assert serve[0] == "predict"
        assert serve[-1] == "check"
