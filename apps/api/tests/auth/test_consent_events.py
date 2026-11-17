"""The consent audit trail: chained, tamper-evident, written by grant and withdraw, no free text."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import consent_events as ev
from app.auth import consent_state as cs
from app.auth import consent_texts as ct
from app.auth.scopes import SCOPE_REGISTRY, read_scopes
from app.auth.service import _shown_texts
from app.config import settings
from app.db.models import ConsentEventRow, ConsentRow
from tests.conftest import World, auth_header


def _rows(db: Session, student_id: str) -> list[ConsentEventRow]:
    db.expire_all()
    return ev.chain(db, uuid.UUID(student_id))


def _grant(client: TestClient, world: World, student: str, scopes: list[str]) -> Any:
    return client.post(
        f"/students/{student}/consent",
        json={"version": "v1", "scopes": scopes},
        headers=auth_header(world.parent_token),
    )


def test_a_grant_writes_one_chained_event_per_scope_and_records_the_text(
    client: TestClient, world: World, db: Session
) -> None:
    res = _grant(client, world, world.student_noshare_id, ["tutoring", "learning_profile"])
    assert res.status_code == 200, res.text
    rows = _rows(db, world.student_noshare_id)
    assert [(r.scope, r.action) for r in rows[-2:]] == [
        ("tutoring", "granted"),
        ("learning_profile", "granted"),
    ]
    assert cs.verify_chain(ev.rows_for_verification(rows))
    consent = db.scalar(select(ConsentRow).where(ConsentRow.id == uuid.UUID(res.json()["id"])))
    assert consent is not None and consent.text_manifest is not None
    shown = consent.text_manifest["learning_profile"]
    assert shown["sha256"]["guardian"] == rows[-1].text_sha256
    assert shown["sha256"] == ct.current_manifest("learning_profile")["sha256"]  # type: ignore[index]
    assert "tutoring" not in consent.text_manifest  # no text file, granted as before
    assert rows[-2].text_sha256 is None


def test_a_scope_with_no_text_is_granted_as_before(
    client: TestClient, world: World, db: Session
) -> None:
    res = _grant(client, world, world.student_noshare_id, ["tutoring"])
    assert res.status_code == 200
    consent = db.get(ConsentRow, uuid.UUID(res.json()["id"]))
    assert consent is not None and consent.text_manifest is None


def test_withdraw_writes_an_event_and_the_chain_still_verifies(
    client: TestClient, world: World, db: Session
) -> None:
    _grant(client, world, world.student_noshare_id, ["tutoring", "learning_profile"])
    res = client.post(
        f"/students/{world.student_noshare_id}/consent/revoke",
        headers=auth_header(world.parent_token),
    )
    assert res.status_code == 200
    rows = _rows(db, world.student_noshare_id)
    assert [(r.scope, r.action) for r in rows[-2:]] == [
        ("tutoring", "withdrawn"),
        ("learning_profile", "withdrawn"),
    ]
    assert cs.verify_chain(ev.rows_for_verification(rows))


def test_dropping_a_scope_on_a_new_grant_is_recorded_as_withdrawn(
    client: TestClient, world: World, db: Session
) -> None:
    _grant(client, world, world.student_noshare_id, ["tutoring", "learning_profile"])
    _grant(client, world, world.student_noshare_id, ["tutoring"])
    actions = [(r.scope, r.action) for r in _rows(db, world.student_noshare_id)]
    assert ("learning_profile", "withdrawn") in actions


def test_editing_a_stored_event_breaks_the_chain(
    client: TestClient, world: World, db: Session
) -> None:
    _grant(client, world, world.student_noshare_id, ["tutoring", "learning_profile"])
    rows = _rows(db, world.student_noshare_id)
    assert cs.verify_chain(ev.rows_for_verification(rows))
    db.execute(
        update(ConsentEventRow).where(ConsentEventRow.id == rows[0].id).values(action="expired")
    )
    db.commit()
    assert not cs.verify_chain(ev.rows_for_verification(_rows(db, world.student_noshare_id)))


def test_an_event_holds_no_free_text_and_no_ip(db: Session) -> None:
    assert {c.name for c in ConsentEventRow.__table__.columns} == {
        "id",
        "at",
        "student_id",
        "guardian_user_id",
        "scope",
        "action",
        "text_sha256",
        "method",
        "actor_kind",
        "prev_hash",
        "row_hash",
    }
    with pytest.raises(ValueError):
        ev.append_event(
            db,
            student_id=uuid.uuid4(),
            guardian_user_id=None,
            scope="tutoring",
            action="a free text reason typed by someone",
            actor_kind="guardian",
        )


def test_the_trail_has_no_foreign_keys_so_it_outlives_the_account() -> None:
    assert not ConsentEventRow.__table__.foreign_keys


def test_a_new_scope_is_refused_while_its_flag_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for scope in ("math_check", "photo_check", "ai_help_typed"):
        flag = SCOPE_REGISTRY[scope].flag_setting
        assert flag and getattr(settings, flag) is False
        with pytest.raises(HTTPException) as err:
            _shown_texts([scope])
        assert err.value.status_code == 400 and "not enabled" in str(err.value.detail)


def test_a_new_scope_is_refused_without_a_verified_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "scope_math_check_enabled", True)
    assert _shown_texts(["math_check"])["math_check"]["version"] == "v1"
    monkeypatch.setattr(ct, "current_manifest", lambda *a, **k: None)
    with pytest.raises(HTTPException) as err:
        _shown_texts(["math_check"])
    assert err.value.status_code == 400 and "text missing" in str(err.value.detail)


def test_a_guardian_cannot_grant_a_new_scope_the_profile_does_not_offer(
    client: TestClient, world: World
) -> None:
    res = _grant(client, world, world.student_noshare_id, ["tutoring", "math_check"])
    assert res.status_code == 400


def test_deprecated_scopes_read_as_their_replacements_and_are_never_written() -> None:
    assert read_scopes(["tutoring", "free_text", "uploads"]) == {
        "tutoring",
        "free_text",
        "uploads",
        "ai_help_typed",
        "photo_check",
    }
    assert read_scopes(["tutoring"]) == {"tutoring"}
