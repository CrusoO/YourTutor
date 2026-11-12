"""UI-1: the topic finder checks typed text in the browser; the server only publishes the rules."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.ask.config import load_safety
from app.ask.guard import EMAIL, PHONE, URL


def test_finder_rules_need_no_login_and_come_from_config(client: TestClient) -> None:
    response = client.get("/context/finder-rules", params={"language": "en"})
    assert response.status_code == 200, response.text
    rules = response.json()
    assert rules["distress_terms"] == list(load_safety("en").distress_terms)
    assert rules["blocked_patterns"] == list(load_safety("en").injection_patterns)
    assert rules["pii"] == {"email": EMAIL.pattern, "phone": PHONE.pattern, "url": URL.pattern}
    assert rules["max_chars"] > 0 and rules["blocked_terms"]


def test_every_published_pattern_compiles(client: TestClient) -> None:
    rules = client.get("/context/finder-rules").json()
    for pattern in [*rules["pii"].values(), *rules["blocked_patterns"]]:
        re.compile(pattern)


def test_an_unknown_language_falls_back_to_the_default_lists(client: TestClient) -> None:
    default = client.get("/context/finder-rules").json()
    other = client.get("/context/finder-rules", params={"language": "zz"}).json()
    assert other["distress_terms"] == default["distress_terms"]


def test_the_rules_endpoint_takes_no_typed_text_and_stores_nothing(client: TestClient) -> None:
    # It is a GET with a language code only; a body or extra parameters are ignored, never kept.
    response = client.get("/context/finder-rules", params={"language": "en", "q": "marker-9d3f"})
    assert response.status_code == 200
    assert "marker-9d3f" not in response.text


def test_finder_rules_carry_the_helplines_so_the_device_can_show_them(client: TestClient) -> None:
    # The topic finder answers a distress phrase on the device and never posts the text, so the
    # numbers it shows must come with the rules (a GET with no user text).
    rules = client.get("/context/finder-rules").json()
    helplines = rules["helplines"]
    assert helplines and all(h["number"] for h in helplines)
    assert {h["kind"] for h in helplines} <= {"mental_health", "child_protection"}
    assert set(helplines[0]) == {"id", "kind", "name", "number", "hours", "verified"}


def test_finder_rules_carry_the_topic_aliases_as_data(client: TestClient) -> None:
    rules = client.get("/context/finder-rules").json()
    aliases = rules["topic_aliases"]
    assert aliases and all(set(a) == {"say", "words", "skill_prefixes"} for a in aliases)
    said = {phrase for a in aliases for phrase in a["say"]}
    assert {"algebra", "trig", "ap", "maths", "quadratic"} <= said
    assert any("MATH.ALG" in a["skill_prefixes"] for a in aliases if "algebra" in a["say"])


def test_aliases_for_a_language_without_a_list_fall_back_to_english(client: TestClient) -> None:
    english = client.get("/context/finder-rules").json()["topic_aliases"]
    hindi = client.get("/context/finder-rules", params={"language": "hi"}).json()["topic_aliases"]
    assert hindi == english  # hi/ne lists are empty until a native speaker writes them
