"""Shared ladder fixtures: the future TypeScript mirror runs the same files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.learner.bkt import BktParams
from app.learner.ladder import LadderEvent, compute
from app.registries.paths import repo_root

FIXTURE_DIR = repo_root() / "packages" / "shared" / "fixtures" / "ladder"
FILES = sorted(FIXTURE_DIR.glob("*.json"))


def _events(raw: list[dict]) -> list[LadderEvent]:
    return [
        LadderEvent(
            event_id=row["event_id"],
            skill_id=row["skill_id"],
            kind=row["kind"],
            at=datetime.fromisoformat(row["at"]),
            item_id=row.get("item_id", ""),
            correct=row.get("correct"),
            pool=row.get("pool", "practice"),
            role=row.get("role", "procedure"),
            structure=row.get("structure", ""),
        )
        for row in raw
    ]


def test_fixture_directory_is_not_empty() -> None:
    assert len(FILES) >= 14


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_ladder_fixture(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    params = {skill: BktParams(**values) for skill, values in data["params"].items()}
    ladders = compute(_events(data["events"]), datetime.fromisoformat(data["now"]), params)
    expected = data["expect"]
    assert set(ladders) == set(expected), path.stem
    for skill, want in expected.items():
        got = ladders[skill].summary()
        assert got["level"] == want["level"], path.stem
        assert got["evidence"] == want["evidence"], path.stem
        for key, value in (want.get("flags") or {}).items():
            assert got["flags"].get(key) == value, (path.stem, key)
