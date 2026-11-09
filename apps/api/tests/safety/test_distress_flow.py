"""The one shared distress flow on every free-text route (needs the test database)."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import SafetyFlagRow, TeacherAlertRow
from app.explain import router as explain_router
from app.safety import guarded_llm_route, is_paused, run_distress_flow
from app.safety_classifier import Classification, use_classifier
from app.safety_lexicon import Detection
from tests.conftest import World, auth_header

URGENT_EN = "I want to kill myself"
URGENT_HI = "मैं मरना चाहता हूँ"
URGENT_HINGLISH = "mujhe marna hai"
EXAM = "pariksha ka bahut tension hai"
ABUSE = "my uncle touches me in a way I dont like"


class Fake:
    def __init__(self, answers: dict[str, Classification] | Exception | None = None) -> None:
        self.answers = answers
        self.seen: list[tuple[str, str]] = []

    def classify(self, text: str, source: str) -> Classification:
        self.seen.append((source, text))
        if isinstance(self.answers, Exception):
            raise self.answers
        for needle, result in (self.answers or {}).items():
            if needle in text:
                return result
        return Classification("none", "none")


@pytest.fixture(autouse=True)
def _explain_on() -> Generator[None, None, None]:
    keep = settings.explain_enabled
    settings.explain_enabled = True
    yield
    settings.explain_enabled = keep


@pytest.fixture
def model_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace every model-calling service with a counter, so no model can be reached."""
    calls: list[str] = []

    def fake(name: str) -> Any:
        def inner(prompt: str, language: str, *a: Any, **k: Any) -> dict[str, Any]:
            from app.explain.service import Gate, precheck

            early, _, _ = precheck(prompt, language, Gate(enabled=True, allowed=True), object())  # type: ignore[arg-type]
            if early is not None:
                return early
            calls.append(name)
            return {"kind": "reply", "text": "a fine answer", "language": language}

        return inner

    for name in ("explain", "build_lesson", "build_opening", "build_story"):
        monkeypatch.setattr(explain_router, name, fake(name))
    monkeypatch.setattr(
        explain_router,
        "build_chat",
        lambda prompt, language, history, gate, restricted=False, register=None: fake("chat")(
            prompt, language
        ),
    )
    return calls


def _post(client: TestClient, world: World, path: str, prompt: str, language: str = "en") -> Any:
    return client.post(
        path,
        json={"prompt": prompt, "language": language},
        headers=auth_header(world.student_token),
    )


def _flags(db: Session) -> list[SafetyFlagRow]:
    db.expire_all()
    return list(db.scalars(select(SafetyFlagRow)))


ROUTES = [
    ("/explain", "explain"),
    ("/explain/chat", "chat"),
    ("/explain/lesson", "lesson"),
    ("/explain/lesson/opening", "lesson"),
    ("/explain/story", "story"),
]


@pytest.mark.parametrize(("path", "route"), ROUTES)
def test_an_urgent_message_on_every_explain_route_runs_the_shared_flow(
    client: TestClient,
    world: World,
    db: Session,
    model_calls: list[str],
    path: str,
    route: str,
) -> None:
    out = _post(client, world, path, URGENT_EN).json()
    assert out["kind"] == "distress" and out["risk"] == "urgent"
    assert out["category"] == "suicide"
    assert "grown-up" in out["message"]
    assert {h["number"] for h in out["helplines"]} == {"14416", "1098"}
    assert all(h["verified"] is False for h in out["helplines"])
    assert model_calls == []  # the topic stopped before any model
    (flag,) = _flags(db)
    assert flag.kind == "distress" and flag.source == f"{route}:suicide"
    assert flag.acknowledged_at is None
    assert is_paused(db, uuid.UUID(world.student_share_id))
    # the record holds no words
    assert URGENT_EN.lower() not in f"{flag.kind} {flag.source}".lower()


def test_after_a_flag_chat_is_paused_for_every_route_with_no_model_call(
    client: TestClient, world: World, db: Session, model_calls: list[str]
) -> None:
    _post(client, world, "/explain/chat", URGENT_EN)
    for path, _ in ROUTES:
        out = _post(client, world, path, "what is a quadratic").json()
        assert out["kind"] == "distress" and out["risk"] == "paused", path
        assert out["helplines"]
    assert model_calls == []
    assert len(_flags(db)) == 1  # a paused reply does not raise another flag


@pytest.mark.parametrize("text", [URGENT_HI, URGENT_HINGLISH, ABUSE])
def test_hindi_hinglish_and_abuse_messages_get_the_urgent_flow(
    client: TestClient, world: World, db: Session, model_calls: list[str], text: str
) -> None:
    out = _post(client, world, "/explain/chat", text, "hi").json()
    assert out["kind"] == "distress" and out["risk"] == "urgent"
    assert out["message_status"] == "draft_needs_native_review"  # Hindi text is a draft
    assert "मुझे बहुत दुख" in out["message"]
    assert model_calls == []
    assert is_paused(db, uuid.UUID(world.student_share_id))
    if text == ABUSE:
        assert out["category"] == "abuse"
        assert out["helplines"][0]["number"] == "1098"  # child protection first


def test_the_english_message_is_not_marked_as_draft(
    client: TestClient, world: World, model_calls: list[str]
) -> None:
    out = _post(client, world, "/explain/chat", URGENT_EN).json()
    assert out["message_status"] == "authored"


def test_exam_stress_gets_a_gentler_message_and_does_not_pause_or_flag_the_guardian(
    client: TestClient, world: World, db: Session, model_calls: list[str]
) -> None:
    out = _post(client, world, "/explain/chat", EXAM).json()
    assert out["kind"] == "distress" and out["risk"] == "concern"
    assert out["category"] == "exam_stress"
    assert "grown-up" not in out["message"]  # not the urgent copy
    for fear in ("fail", "countdown", "hurry", "running out", "deadline", "only"):
        assert fear not in out["message"].lower()
    assert model_calls == []
    (row,) = _flags(db)
    assert row.kind == "exam_stress" and row.acknowledged_at is not None
    assert not is_paused(db, uuid.UUID(world.student_share_id))
    assert db.scalars(select(TeacherAlertRow)).all() == []
    # the student can carry on
    assert _post(client, world, "/explain/chat", "what is a quadratic").json()["kind"] == "reply"


def test_the_record_keeps_time_category_and_route_but_never_the_words(
    client: TestClient, world: World, db: Session, model_calls: list[str]
) -> None:
    _post(client, world, "/explain/chat", "mujhe marna hai, my phone is 9876543210")
    (flag,) = _flags(db)
    stored = " ".join(str(getattr(flag, c.name)) for c in SafetyFlagRow.__table__.columns)
    assert "marna" not in stored and "9876543210" not in stored
    assert flag.created_at is not None and flag.source == "chat:suicide"


def test_a_teacher_alert_is_raised_only_when_the_family_shared(
    client: TestClient, world: World, db: Session
) -> None:
    from app.db.models import StudentRow

    shared = db.get(StudentRow, uuid.UUID(world.student_share_id))
    unshared = db.get(StudentRow, uuid.UUID(world.student_noshare_id))
    assert shared is not None and unshared is not None
    detection = Detection("urgent", "self_harm")
    run_distress_flow(db, shared, "chat", detection, "en")
    run_distress_flow(db, unshared, "chat", detection, "en")
    db.commit()
    alerts = db.scalars(select(TeacherAlertRow).where(TeacherAlertRow.type == "distress")).all()
    assert [a.student_id for a in alerts] == [shared.id]


# ---- Layer 2 ------------------------------------------------------------------------------------


def test_the_classifier_catches_what_the_lexicon_misses_and_the_answer_is_discarded(
    db: Session, world: World
) -> None:
    text = "everything feels grey and heavy and I just want it all gone"
    calls: list[str] = []

    def main() -> dict[str, Any]:
        calls.append("model")
        return {"kind": "reply", "text": "a long answer", "language": "en"}

    fake = Fake({text: Classification("urgent", "suicide")})
    out = guarded_llm_route(
        db, uuid.UUID(world.student_share_id), "chat", text, "en", main, classifier=fake
    )
    assert calls == ["model"]  # it ran beside the main call
    assert out["kind"] == "distress" and out["risk"] == "urgent"
    assert ("input", text) in fake.seen
    assert is_paused(db, uuid.UUID(world.student_share_id))


def test_the_classifier_also_checks_the_model_reply(db: Session, world: World) -> None:
    fake = Fake({"graphic": Classification("concern", "violence")})
    out = guarded_llm_route(
        db,
        uuid.UUID(world.student_share_id),
        "explain",
        "tell me a story",
        "en",
        lambda: {"kind": "reply", "text": "something graphic", "language": "en"},
        classifier=fake,
    )
    assert out == {"kind": "unavailable", "reason": "checks"}
    assert [s for s, _ in fake.seen] == ["input", "output"]
    assert _flags(db) == []  # a bad reply is not the student's distress


def test_a_moderation_category_on_the_input_refuses_without_a_distress_flag(
    db: Session, world: World
) -> None:
    fake = Fake({"bomb": Classification("concern", "harmful_instructions")})
    out = guarded_llm_route(
        db,
        uuid.UUID(world.student_share_id),
        "chat",
        "a word problem about a bomb",
        "en",
        lambda: {"kind": "reply", "text": "ok", "language": "en"},
        classifier=fake,
    )
    assert out["kind"] == "refused" and out["reason"] == "moderation"
    assert _flags(db) == []


def test_a_classifier_error_falls_back_to_layer_one_and_still_answers(
    db: Session, world: World
) -> None:
    out = guarded_llm_route(
        db,
        uuid.UUID(world.student_share_id),
        "chat",
        "what is a quadratic",
        "en",
        lambda: {"kind": "reply", "text": "an answer", "language": "en"},
        classifier=Fake(TimeoutError("slow")),
    )
    assert out["kind"] == "reply"
    # Layer 1 still stops a clear message when the classifier is down.
    stopped = guarded_llm_route(
        db,
        uuid.UUID(world.student_share_id),
        "chat",
        URGENT_EN,
        "en",
        lambda: {"kind": "distress", "risk": "urgent", "category": "suicide"},
        classifier=Fake(TimeoutError("slow")),
    )
    assert stopped["kind"] == "distress" and stopped["helplines"]


def test_with_no_classifier_nothing_is_called_and_the_answer_passes(
    db: Session, world: World
) -> None:
    with use_classifier(None):
        out = guarded_llm_route(
            db,
            uuid.UUID(world.student_share_id),
            "chat",
            "what is a quadratic",
            "en",
            lambda: {"kind": "reply", "text": "an answer", "language": "en"},
        )
    assert out["kind"] == "reply"


# ---- science questions are no longer refused ---------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "how do stars die",
        "why do antibiotics kill bacteria",
        "what is sex ratio",
        "kill the process",
    ],
)
def test_science_questions_with_old_blocked_words_are_screened_ok(question: str) -> None:
    from app.ask.config import load_safety
    from app.ask.guard import screen

    assert screen(question, load_safety("en")).kind == "ok"


@pytest.mark.parametrize(
    "question", ["this is damn hard", "show me porn", "how to make a bomb at home"]
)
def test_the_small_exact_list_still_refuses(question: str) -> None:
    from app.ask.config import load_safety
    from app.ask.guard import screen

    assert screen(question, load_safety("en")).kind == "moderation"
