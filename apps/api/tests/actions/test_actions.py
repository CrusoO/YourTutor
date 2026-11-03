"""A1: the deterministic action router. Pure matching and routing first, then the endpoint."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.actions.matcher import load_action_config, match_utterance, normalise
from app.actions.registry import REGISTRY, ActionSpec, Risk, Tier
from app.actions.service import route
from app.ask.guard import Verdict
from app.registries.paths import config_dir
from tests.conftest import World, auth_header

CONFIG = load_action_config()


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


# -- matching: exact after filler words, never partial --------------------------------------------


@pytest.mark.parametrize(
    ("text", "action", "value"),
    [
        ("practice", "start_practice", None),
        ("Please, can you quiz me?", "start_practice", None),
        ("  START   PRACTICE!! ", "start_practice", None),
        ("continue where I left off", "continue_learning", None),
        ("show my subjects", "show_subjects", None),
        ("switch to Hindi", "switch_language", "hi"),
        ("English please", "switch_language", "en"),
        ("let's start over", "new_chat", None),
        ("what can you do?", "help", None),
    ],
)
def test_phrases_match(text: str, action: str, value: str | None) -> None:
    hit = match_utterance(text, CONFIG, "en")
    assert hit is not None and (hit.action, hit.value) == (action, value)


@pytest.mark.parametrize(
    "text",
    [
        "what is practice in physics",
        "how do I solve a quadratic",
        "practice makes perfect",
        "continue the story of the french revolution",
        "switch to hindi and then explain slope to me please",
        "",
        "   ",
        "?!",
    ],
)
def test_questions_and_noise_are_not_actions(text: str) -> None:
    assert match_utterance(text, CONFIG, "en") is None


def test_an_unknown_language_falls_back_to_the_default_block() -> None:
    hit = match_utterance("practice", CONFIG, "xx")
    assert hit is not None and hit.action == "start_practice"


def test_normalise_keeps_indic_combining_marks() -> None:
    assert normalise("हिन्दी!", frozenset()) == "हिन्दी"


# -- routing: tiers, risk, safety -----------------------------------------------------------------


def test_a_safe_action_runs_with_validated_arguments() -> None:
    assert route("switch to hindi", "en", Tier.GUEST) == {
        "kind": "action",
        "name": "switch_language",
        "client": "set_language",
        "args": {"language": "hi"},
        "risk": "safe",
        "narration": "Okay, changing the language.",
    }


def test_the_reply_never_echoes_the_students_words() -> None:
    out = str(route("please quiz me", "en", Tier.STUDENT)).lower()
    assert "quiz" not in out and "please" not in out


def test_a_confirm_action_asks_first() -> None:
    out = route("new chat", "en", Tier.STUDENT)
    assert out["kind"] == "action" and out["risk"] == "confirm" and out["confirm"]


def test_guest_only_action_is_denied_to_a_signed_in_student() -> None:
    assert route("sign in", "en", Tier.GUEST)["kind"] == "action"
    assert route("sign in", "en", Tier.STUDENT) == {
        "kind": "denied",
        "name": "sign_in_prompt",
        "narration": "You are already signed in.",
    }


@pytest.mark.parametrize("kind", ["distress", "injection", "moderation"])
def test_an_unsafe_or_distressed_message_is_never_an_action(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    monkeypatch.setattr("app.actions.service.screen", lambda *_a, **_k: Verdict(kind))
    assert route("practice", "en", Tier.STUDENT) == {"kind": "none"}


def test_too_long_and_empty_messages_do_nothing() -> None:
    assert route("practice " * 40, "en", Tier.STUDENT) == {"kind": "none"}
    assert route("   ", "en", Tier.STUDENT) == {"kind": "none"}


def test_a_value_the_registry_rejects_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = REGISTRY["switch_language"]
    narrow = ActionSpec(
        spec.name,
        spec.client,
        Risk.SAFE,
        spec.tiers,
        arg_name="language",
        arg_values=frozenset({"en"}),
    )
    monkeypatch.setattr("app.actions.service.REGISTRY", {**REGISTRY, spec.name: narrow})
    assert route("hindi", "en", Tier.STUDENT) == {"kind": "none"}


def test_the_registry_is_closed_and_has_no_pedagogy_or_data_actions() -> None:
    forbidden = ("mark", "grade", "answer", "hint", "teach", "explain", "delete", "buy", "share")
    assert not [name for name in REGISTRY if any(word in name for word in forbidden)]
    verbs = {"start_practice", "open_screen", "set_language", "new_chat", "none"}
    assert {spec.client for spec in REGISTRY.values()} <= verbs
    with pytest.raises(TypeError):
        REGISTRY["x"] = REGISTRY["help"]  # type: ignore[index]


# -- the endpoint ---------------------------------------------------------------------------------


def test_endpoint_needs_a_student(client: TestClient, world: World) -> None:
    r = client.post(
        "/actions/route",
        json={"utterance": "practice"},
        headers=auth_header(world.parent_token),
    )
    assert r.status_code == 403


def test_endpoint_routes_for_a_student(client: TestClient, world: World) -> None:
    headers = auth_header(world.student_token)
    r = client.post("/actions/route", json={"utterance": "practice"}, headers=headers)
    assert r.status_code == 200 and r.json()["name"] == "start_practice"
    miss = client.post("/actions/route", json={"utterance": "why is the sky blue"}, headers=headers)
    assert miss.json() == {"kind": "none"}


def test_endpoint_treats_a_guest_as_the_guest_tier(client: TestClient) -> None:
    started = client.post(
        "/guest/start", json={"curriculum_id": "bhutan", "grade": 9, "subject": "math"}
    )
    assert started.status_code == 200, started.text
    headers = auth_header(started.json()["token"])
    r = client.post("/actions/route", json={"utterance": "sign in"}, headers=headers)
    assert r.json()["kind"] == "action" and r.json()["name"] == "sign_in_prompt"


def test_endpoint_rejects_unknown_fields_and_tolerates_a_bad_language(
    client: TestClient, world: World
) -> None:
    headers = auth_header(world.student_token)
    bad = client.post("/actions/route", json={"utterance": "practice", "x": 1}, headers=headers)
    assert bad.status_code == 422
    ok = client.post(
        "/actions/route", json={"utterance": "practice", "language": "zz"}, headers=headers
    )
    assert ok.status_code == 200 and ok.json()["kind"] == "action"
