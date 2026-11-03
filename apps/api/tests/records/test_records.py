"""The learning card kept in an account: who may keep one, what is stored, and what is dropped."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.records.service import MAX_ITEMS, MAX_LESSONS, clean_item, clean_record
from tests.conftest import World, auth_header

URL = "/students/me/lesson-records"


def _record(topic: str = "photosynthesis", at: str = "2026-11-01T10:00:00Z") -> dict[str, Any]:
    return {
        "topic": topic,
        "at": at,
        "items": [
            {
                "id": "1",
                "kind": "predict",
                "right": False,
                "confidence": "sure",
                "idea": "plants eat soil",
            },
            {"id": "4", "kind": "check", "right": True, "confidence": None, "idea": None},
        ],
    }


def test_a_signed_in_learner_keeps_and_reads_back_a_card(client: TestClient, world: World) -> None:
    head = auth_header(world.student_token)
    out = client.post(URL, json={"records": [_record()]}, headers=head)
    assert out.status_code == 200 and out.json() == {"saved": 1}
    got = client.get(URL, headers=head).json()["records"]
    assert [r["topic"] for r in got] == ["photosynthesis"]
    assert got[0]["items"][0] == {
        "id": "1",
        "kind": "predict",
        "right": False,
        "confidence": "sure",
        "idea": "plants eat soil",
    }


def test_sending_the_same_lesson_twice_keeps_one(client: TestClient, world: World) -> None:
    head = auth_header(world.student_token)
    client.post(URL, json={"records": [_record()]}, headers=head)
    again = client.post(URL, json={"records": [_record()]}, headers=head)
    assert again.json() == {"saved": 0}
    assert len(client.get(URL, headers=head).json()["records"]) == 1


def test_only_the_latest_lessons_are_kept(client: TestClient, world: World) -> None:
    head = auth_header(world.student_token)
    records = [_record(f"topic {i}", f"2026-10-{i + 1:02d}T10:00:00Z") for i in range(MAX_LESSONS)]
    client.post(URL, json={"records": records}, headers=head)
    client.post(URL, json={"records": [_record("newest", "2026-11-02T10:00:00Z")]}, headers=head)
    got = client.get(URL, headers=head).json()["records"]
    assert len(got) == MAX_LESSONS
    assert got[0]["topic"] == "newest" and "topic 0" not in {r["topic"] for r in got}


def test_a_guest_cannot_keep_a_card_in_an_account(client: TestClient) -> None:
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    head = auth_header(guest["token"])
    assert client.post(URL, json={"records": [_record()]}, headers=head).status_code == 403
    assert client.get(URL, headers=head).status_code == 403


def test_nobody_can_do_it_without_signing_in_as_a_learner(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code in (401, 403)
    assert client.get(URL, headers=auth_header(world.parent_token)).status_code == 403


def test_the_learner_can_clear_the_card(client: TestClient, world: World) -> None:
    head = auth_header(world.student_token)
    client.post(URL, json={"records": [_record()]}, headers=head)
    assert client.delete(URL, headers=head).json() == {"cleared": True}
    assert client.get(URL, headers=head).json() == {"records": []}


def test_nonsense_is_dropped_not_stored(client: TestClient, world: World) -> None:
    head = auth_header(world.student_token)
    bad: list[Any] = [
        {"topic": "", "at": "2026-11-01T10:00:00Z", "items": [_record()["items"][0]]},
        {"topic": "x", "at": "not a date", "items": [_record()["items"][0]]},
        {"topic": "x", "at": "2026-11-01T10:00:00", "items": [_record()["items"][0]]},  # no zone
        {"topic": "x", "at": "2026-11-01T10:00:00Z", "items": []},
        {"topic": "x", "at": "2026-11-01T10:00:00Z", "items": "all"},
    ]
    assert client.post(URL, json={"records": bad}, headers=head).json() == {"saved": 0}
    too_many = {"records": [_record(f"t{i}") for i in range(MAX_LESSONS + 1)]}
    assert client.post(URL, json=too_many, headers=head).status_code == 422


def test_items_are_cleaned_and_capped() -> None:
    assert clean_item({"id": "1", "kind": "quiz", "right": True}) is None
    assert clean_item({"id": "1", "kind": "check", "right": "yes"}) is None
    assert clean_item({"id": "", "kind": "check", "right": True}) is None
    right = clean_item(
        {"id": "1", "kind": "check", "right": True, "idea": "ignored", "confidence": "maybe"}
    )
    assert right == {"id": "1", "kind": "check", "right": True, "confidence": None, "idea": None}
    long = clean_item({"id": "1", "kind": "check", "right": False, "idea": "x" * 500})
    assert long is not None and len(long["idea"]) == 80
    many: dict[str, Any] = {"topic": "t", "at": "2026-11-01T10:00:00Z"}
    many["items"] = [{"id": str(i), "kind": "check", "right": True} for i in range(MAX_ITEMS + 5)]
    cleaned = clean_record(many)
    assert cleaned is not None and len(cleaned[2]) == MAX_ITEMS
