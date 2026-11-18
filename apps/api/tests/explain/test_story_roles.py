"""Story prompt v3: the six-part template and the role fields (fake provider, no live model)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.explain.service import Gate
from app.explain.story import (
    PROMPTS,
    build_story,
    handoff_issues,
    plan_prompt,
    prompt_version,
    sanitise_roles,
    scenes_prompt,
)
from app.llm.provider import FakeProvider

OPEN = Gate(enabled=True, allowed=True)
ENV = "EXPLAIN_STORY_PROMPT_VERSION"


def _plan() -> str:
    roles = ["hook", "build", "reveal", "wrap"]
    scenes = [
        {"role": r, "heading": f"Scene {i}", "purpose": r, "story": f"Idea {i}.", "picture": "x"}
        for i, r in enumerate(roles)
    ]
    return json.dumps({"title": "Sum of roots", "scenes": scenes})


def _scene(i: int, last: str = "Your turn: try a sum of roots question.") -> dict[str, Any]:
    return {
        "heading": f"Part {i}",
        "sentences": [f"The sum of roots is key {i}.", last],
        "visuals": [{"kind": "circle", "cx": "5+t", "cy": 20, "r": 4, "role": "term"}],
        "highlights": [{"s": 0, "word": "sum", "role": "term"}],
    }


def _reply(**over: Any) -> str:
    scenes = [_scene(i) for i in range(4)]
    scenes[0]["sentences"][-1] = "What is the sum of the roots?"
    scenes[0].update(over)
    return json.dumps({"scenes": scenes})


def test_default_is_v2_and_only_the_setting_selects_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV, raising=False)
    assert prompt_version() == "v2"
    assert "+roles" not in plan_prompt("q", False).version
    monkeypatch.setenv(ENV, "v2")
    assert prompt_version() == "v2"
    monkeypatch.setenv(ENV, "v3")
    assert prompt_version() == "v3"
    assert plan_prompt("q", False).version.endswith("+roles")
    assert "TEACHING TEMPLATE" in plan_prompt("q", False).system
    assert "TEACHING TEMPLATE" in scenes_prompt("q", json.loads(_plan()), "animated").system


def test_v2_story_ignores_role_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV, raising=False)
    out = build_story("q", "en", OPEN, FakeProvider([_plan(), _reply()]), "m")
    assert out["kind"] == "story"
    assert "highlights" not in out["story"]["scenes"][0]
    assert "role_notes" not in out
    assert "TEACHING TEMPLATE" not in scenes_prompt("q", json.loads(_plan())).system


def test_v3_passes_valid_fields_through_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, "v3")
    out = build_story("q", "en", OPEN, FakeProvider([_plan(), _reply()]), "m")
    sc = out["story"]["scenes"][0]
    assert sc["highlights"] == [{"s": 0, "word": "sum", "role": "term"}]
    assert sc["visuals"][0]["role"] == "term"
    assert "role_notes" not in out


def test_v3_scenes_prompt_lists_verified_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, "v3")
    p = scenes_prompt("q", json.loads(_plan()), "animated", ["-3"])
    assert "role checked): -3" in p.user


def test_closed_list_and_highlight_word_rules() -> None:
    scene: dict[str, Any] = {
        "sentences": ["The sum is here.", "Another line."],
        "visuals": [{"kind": "circle", "role": "sparkly"}, {"kind": "rect", "role": "term"}],
        "highlights": [
            {"s": 0, "word": "sum", "role": "term"},
            {"s": 1, "word": "sum", "role": "term"},
            {"s": 0, "word": "sum", "role": "neon"},
            {"s": 9, "word": "sum", "role": "term"},
            {"s": 0, "word": "su", "role": "term"},
        ],
    }
    notes = sanitise_roles([scene])
    assert scene["highlights"] == [{"s": 0, "word": "sum", "role": "term"}]
    assert "role" not in scene["visuals"][0] and scene["visuals"][1]["role"] == "term"
    assert len(notes) == 5


def test_checked_needs_a_verified_value() -> None:
    def make() -> dict[str, Any]:
        return {
            "sentences": ["The roots add to -3 here."],
            "visuals": [{"kind": "circle", "role": "checked"}],
            "highlights": [{"s": 0, "word": "-3", "role": "checked"}],
        }

    a = make()
    assert len(sanitise_roles([a])) == 2
    assert "highlights" not in a and "role" not in a["visuals"][0]
    b = make()
    assert sanitise_roles([b], ["-3"]) == []
    assert b["highlights"][0]["role"] == "checked"
    c = make()
    c["highlights"][0] = {"s": 0, "word": "roots", "role": "checked"}
    assert len(sanitise_roles([c], ["-3"])) == 1  # the word is not a verified value


def test_at_most_one_key_per_scene() -> None:
    scene = {
        "sentences": ["The sum is key."],
        "visuals": [{"kind": "a", "role": "key"}, {"kind": "b", "role": "key"}],
        "highlights": [{"s": 0, "word": "key", "role": "key"}],
    }
    assert len(sanitise_roles([scene])) == 2


def test_handoff_sentence_rule() -> None:
    ok = [{"sentences": ["Recap.", "Your turn: try a sum of roots question."]}]
    assert handoff_issues(ok) == []
    assert handoff_issues([{"sentences": []}])  # missing
    assert handoff_issues([{"sentences": ["That is all."]}])  # no invitation
    assert handoff_issues([{"sentences": ["Your turn: the answer is 5."]}])  # reveals a digit


def test_v3_flags_a_bad_handoff_in_the_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, "v3")
    scenes = [_scene(i) for i in range(4)]
    scenes[0]["sentences"][-1] = "What is the sum of the roots?"
    scenes[3]["sentences"][-1] = "So the answer is 5."
    out = build_story("q", "en", OPEN, FakeProvider([_plan(), json.dumps({"scenes": scenes})]), "m")
    assert any("last sentence" in n for n in out["role_notes"])


def test_prompt_files_carry_the_template_and_role_rules() -> None:
    for name in ("story_plan.v3.md", "story_scenes.v3.md"):
        text = (PROMPTS / name).read_text(encoding="utf-8").lower()
        for needle in ("hook", "wrap", "your turn", "term", "key", "look-again", "checked"):
            assert needle in text, (name, needle)
        assert "verified solver input" in text
        assert "colour as the only signal" in text
        assert "one new idea" in text.lower()
    # v2 stays untouched and does not know the roles
    assert "look-again" not in (PROMPTS / "story_plan.v2.md").read_text(encoding="utf-8")
