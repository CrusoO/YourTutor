"""The store: id validation, gates, sealing, decay, export, revoke, retention."""

from __future__ import annotations

import base64
import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import retention
from app.auth.sender import MemoryOtpSender
from app.config import settings
from app.db.models import LearnerMethodCountRow
from app.learner.profile import store
from app.learner.profile.counts import week_index
from app.learner.profile.crypto import KeyRing, ProfileCryptoError, build_aad, unseal
from tests.conftest import auth_header, signup

TODAY = date(2027, 6, 1)
SCOPES = ["tutoring", "learning_profile"]


@pytest.fixture
def ring() -> KeyRing:
    return KeyRing(((1, os.urandom(32)),))


@pytest.fixture
def learner(client: TestClient, sender: MemoryOtpSender, db: Session) -> tuple[uuid.UUID, str]:
    token = signup(client, sender, "guardian@example.com")
    res = client.post(
        "/students",
        json={"display_name": "Ava", "grade": 9, "board": "bhutan"},
        headers=auth_header(token),
    )
    assert res.status_code == 200, res.text
    return uuid.UUID(res.json()["id"]), token


def _grant(client: TestClient, sid: uuid.UUID, token: str, scopes: list[str]) -> None:
    res = client.post(
        f"/students/{sid}/consent",
        json={"version": "v1", "scopes": scopes},
        headers=auth_header(token),
    )
    assert res.status_code == 200, res.text


def _rows(db: Session) -> list[LearnerMethodCountRow]:
    db.expire_all()
    return list(db.scalars(select(LearnerMethodCountRow)))


@pytest.mark.parametrize("bad", ["", "a b", "x-y", "é", "ß_step", "1abc", "a" * 65])
def test_a_letter_or_shape_outside_the_id_charset_is_refused(
    db: Session, ring: KeyRing, bad: str
) -> None:
    sid = uuid.uuid4()
    with pytest.raises(ValueError):
        store.record_event(db, sid, "MATH.ALG.X", method_id=bad, ring=ring)
    with pytest.raises(ValueError):
        store.record_event(db, sid, "MATH.ALG.X", error_id=bad, ring=ring)
    with pytest.raises(ValueError):
        store.record_event(db, sid, bad, method_id="factorise", ring=ring)
    assert _rows(db) == []


@pytest.mark.parametrize("inc", [0, -1, 11, 1.5, "2", True, None])
def test_increment_must_be_a_small_integer(db: Session, ring: KeyRing, inc: object) -> None:
    with pytest.raises(ValueError):
        store.record_event(db, uuid.uuid4(), "S", method_id="m", increment=inc, ring=ring)  # type: ignore[arg-type]


def test_exactly_one_of_method_or_error(db: Session, ring: KeyRing) -> None:
    with pytest.raises(ValueError):
        store.record_event(db, uuid.uuid4(), "S", ring=ring)
    with pytest.raises(ValueError):
        store.record_event(db, uuid.uuid4(), "S", method_id="a", error_id="b", ring=ring)


def test_flag_off_writes_nothing(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str], ring: KeyRing
) -> None:
    sid, token = learner
    _grant(client, sid, token, SCOPES)
    assert settings.learner_profile_enabled is False
    assert store.record_event(db, sid, "S", method_id="m", ring=ring) is False
    assert store.read_counts(db, sid, "S", ring=ring) is None
    assert _rows(db) == []


def test_no_scope_writes_nothing(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str], ring: KeyRing
) -> None:
    sid, token = learner
    settings.learner_profile_enabled = True
    _grant(client, sid, token, ["tutoring"])
    assert store.record_event(db, sid, "S", method_id="m", ring=ring) is False
    assert _rows(db) == []


def test_empty_key_ring_writes_nothing(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str]
) -> None:
    sid, token = learner
    settings.learner_profile_enabled = True
    settings.profile_enc_keys = ""
    _grant(client, sid, token, SCOPES)
    assert store.record_event(db, sid, "S", method_id="m") is False
    assert _rows(db) == []


def test_write_read_seal_decay_and_aad_binding(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str], ring: KeyRing
) -> None:
    sid, token = learner
    settings.learner_profile_enabled = True
    _grant(client, sid, token, SCOPES)
    assert store.record_event(db, sid, "S", method_id="factorise", today=TODAY, ring=ring)
    assert store.record_event(
        db, sid, "S", error_id=store.DiagnosisClass.SLIP, increment=2, today=TODAY, ring=ring
    )
    (row,) = _rows(db)
    assert b"factorise" not in row.payload and row.updated_week == week_index(TODAY)
    counts = store.read_counts(db, sid, "S", today=TODAY, ring=ring)
    assert counts is not None
    assert counts.methods == {"factorise": 1.0} and counts.errors == {"slip": 2.0}
    later = store.read_counts(db, sid, "S", today=TODAY + timedelta(weeks=20), ring=ring)
    assert later is not None and later.methods == {} and later.errors == {}
    with pytest.raises(ProfileCryptoError):  # a copied row opens nowhere else
        unseal(ring, row.key_id, row.payload, build_aad(uuid.uuid4(), "S", row.schema_v))
    settings.profile_enc_keys = "1:" + base64.b64encode(ring.keys[0][1]).decode()
    assert store.key_ring().keys == ring.keys


def test_export_shows_plain_counts_and_survives_a_lost_key(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str], ring: KeyRing
) -> None:
    sid, token = learner
    settings.learner_profile_enabled = True
    _grant(client, sid, token, SCOPES)
    store.record_event(db, sid, "S", method_id="factorise", today=TODAY, ring=ring)
    (entry,) = store.export_rows(db, sid, today=TODAY, ring=ring)
    assert entry["methods"] == {"factorise": 1.0} and "payload" not in entry
    (lost,) = store.export_rows(db, sid, today=TODAY, ring=KeyRing(((9, os.urandom(32)),)))
    assert lost["readable"] is False and "methods" not in lost


def test_revoke_and_grant_without_the_scope_delete_rows(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str], ring: KeyRing
) -> None:
    sid, token = learner
    settings.learner_profile_enabled = True
    _grant(client, sid, token, SCOPES)
    store.record_event(db, sid, "S", method_id="m", ring=ring)
    db.commit()
    assert len(_rows(db)) == 1
    _grant(client, sid, token, SCOPES)  # an unchanged scope keeps the rows
    assert len(_rows(db)) == 1
    _grant(client, sid, token, ["tutoring"])  # dropping the scope deletes them
    assert _rows(db) == []
    _grant(client, sid, token, SCOPES)
    store.record_event(db, sid, "S", method_id="m", ring=ring)
    db.commit()
    res = client.post(f"/students/{sid}/consent/revoke", headers=auth_header(token))
    assert res.status_code == 200
    assert _rows(db) == []


def test_retention_job_deletes_only_old_rows_and_dry_run_changes_nothing(
    client: TestClient, db: Session, learner: tuple[uuid.UUID, str], ring: KeyRing
) -> None:
    sid, token = learner
    settings.learner_profile_enabled = True
    _grant(client, sid, token, SCOPES)
    old, new = TODAY - timedelta(weeks=27), TODAY - timedelta(weeks=25)
    store.record_event(db, sid, "OLD", method_id="m", today=old, ring=ring)
    store.record_event(db, sid, "NEW", method_id="m", today=new, ring=ring)
    db.commit()
    now = datetime(TODAY.year, TODAY.month, TODAY.day, tzinfo=UTC)
    assert retention.run_job(db, "profile_counts", dry_run=True, now=now).endswith("1 row(s)")
    assert len(_rows(db)) == 2
    assert "deleted 1 row(s)" in retention.run_job(db, "profile_counts", now=now)
    assert [r.skill_id for r in _rows(db)] == ["NEW"]
    assert "profile_counts" in retention.JOBS


def test_pseudonym_is_stable_salted_and_short() -> None:
    sid = uuid.uuid4()
    a = store.pseudonym(sid, "s" * 20)
    assert a == store.pseudonym(sid, "s" * 20) and len(a) == 16
    assert a != store.pseudonym(sid, "t" * 20) and str(sid) not in a
    with pytest.raises(ValueError):
        store.pseudonym(sid, "")
