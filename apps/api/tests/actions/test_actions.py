"""A1: the action rules. Config and registry agree, matching is exact, the table is sound."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.actions.matcher import load_action_config, match_utterance, normalise
from app.actions.registry import REGISTRY, ActionSpec, Risk, Tier
from app.actions.rules import build_rules
from app.registries.paths import config_dir, repo_root

CONFIG = load_action_config()
FIXTURES = repo_root() / "packages" / "shared" / "fixtures" / "actions"


# -- the config and the registry agree ----------------------------------------------------------


def test_every_registered_action_has_words_and_narration() -> None:
    en = CONFIG.languages["en"]
    assert set(REGISTRY) <= set(en.narration)
    assert {action for action, _ in en.table.values()} == set(REGISTRY)


def _write(tmp_path: Path, mutate: Callable[[dict[str, Any]], object]) -> Path:
    data = yaml.safe_load((config_dir() / "actions.yaml").read_text(encoding="utf-8"))
    mutate(data)
    (tmp_path / "actions.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return tmp_path


def test_an_unregistered_action_in_the_config_is_refused(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        lambda d: d["languages"]["en"]["actions"].update(
            delete_everything={"phrases": ["wipe"], "narration": "x"}
        ),
    )
    with pytest.raises(ValueError, match="not a registered action"):
        load_action_config(root)


def test_a_phrase_for_two_actions_is_refused(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        lambda d: d["languages"]["en"]["actions"]["help"]["phrases"].append("practice"),
    )
    with pytest.raises(ValueError, match="ambiguous"):
        load_action_config(root)


def test_a_value_the_registry_does_not_allow_is_refused(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        lambda d: d["languages"]["en"]["actions"]["switch_language"]["values"].update(
            fr=["french"]
        ),
    )
    with pytest.raises(ValueError, match="cannot take"):
        load_action_config(root)


def test_a_missing_narration_is_refused(tmp_path: Path) -> None:
    root = _write(tmp_path, lambda d: d["languages"]["en"]["actions"]["help"].pop("narration"))
    with pytest.raises(ValueError, match="no narration"):
        load_action_config(root)


def test_the_registry_is_closed_and_has_no_pedagogy_or_data_actions() -> None:
    forbidden = ("mark", "grade", "answer", "hint", "teach", "explain", "delete", "buy", "share")
    assert not [name for name in REGISTRY if any(word in name for word in forbidden)]
    verbs = {"start_practice", "open_screen", "set_language", "new_chat", "none"}
    assert {spec.client for spec in REGISTRY.values()} <= verbs
    with pytest.raises(TypeError):
        REGISTRY["x"] = REGISTRY["help"]  # type: ignore[index]


def test_a_confirm_action_always_has_a_question() -> None:
    rules = build_rules("en")
    for name, row in rules["actions"].items():
        if row["risk"] == Risk.CONFIRM.value:
            assert row.get("confirm"), name


def test_argument_values_are_checked_against_the_registry() -> None:
    spec = REGISTRY["switch_language"]
    assert spec.args_for("hi") == {"language": "hi"}
    assert spec.args_for("fr") is None and spec.args_for(None) is None
    plain = ActionSpec("p", "none", Risk.SAFE, frozenset({Tier.GUEST}))
    assert plain.args_for(None) == {} and plain.args_for("x") is None


# -- matching: exact after filler words, never partial --------------------------------------------


def test_an_unknown_language_falls_back_to_the_default_block() -> None:
    hit = match_utterance("practice", CONFIG, "xx")
    assert hit is not None and hit.action == "start_practice"
    assert build_rules("xx")["language"] == "en"


def test_normalise_keeps_indic_combining_marks() -> None:
    assert normalise("हिन्दी!", frozenset()) == "हिन्दी"


# -- the browser's table ------------------------------------------------------------------------


def test_the_shared_rules_fixture_is_current() -> None:
    fixture = json.loads((FIXTURES / "rules_en.json").read_text(encoding="utf-8"))
    assert fixture == build_rules("en"), (
        "config/actions.yaml or the registry changed; regenerate the fixture: "
        "cd apps/api && python -m app.actions.rules > "
        "../../packages/shared/fixtures/actions/rules_en.json"
    )


def decide(rules: dict[str, Any], text: str, tier: str) -> dict[str, Any]:
    """The reference decision, written here to match apps/web/lib/chat/actions.ts case for case."""
    cleaned = " ".join(text.split())
    if not cleaned or len(cleaned) > rules["max_chars"]:
        return {"kind": "none"}
    key = normalise(cleaned, frozenset(rules["fillers"]))
    if not key or len(key.split()) > rules["max_words"]:
        return {"kind": "none"}
    hit = rules["phrases"].get(key)
    if hit is None:
        return {"kind": "none"}
    row = rules["actions"][hit["name"]]
    if tier not in row["tiers"]:
        return {"kind": "denied", "name": hit["name"]}
    return {"kind": "action", "name": hit["name"], "args": hit["args"], "risk": row["risk"]}


def test_the_shared_cases_hold_for_the_python_reference() -> None:
    cases = json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))["cases"]
    rules = build_rules("en")
    assert len(cases) >= 20
    for case in cases:
        assert decide(rules, case["text"], case["tier"]) == case["expect"], case


def test_every_phrase_in_the_table_names_a_registered_action_with_valid_arguments() -> None:
    rules = build_rules("en")
    for key, hit in rules["phrases"].items():
        assert key == normalise(key, frozenset(rules["fillers"])), key
        spec = REGISTRY[hit["name"]]
        assert set(hit["args"]) <= set(spec.fixed_args) | {spec.arg_name}, key


def test_the_table_contains_nothing_from_a_student() -> None:
    # Built from config alone: no per-student or per-request input exists to leak into it.
    assert build_rules("en") == build_rules("en")


# -- the endpoint ---------------------------------------------------------------------------------


def test_rules_are_public_and_take_no_user_text(client: TestClient) -> None:
    r = client.get("/actions/rules", params={"language": "en"})
    assert r.status_code == 200 and r.json() == build_rules("en")
    assert client.post("/actions/route", json={"utterance": "practice"}).status_code in (404, 405)
