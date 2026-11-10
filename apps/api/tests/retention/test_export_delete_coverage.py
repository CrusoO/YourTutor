"""Export includes the learner's records and nothing of another family's; delete leaves no row.

In-memory SQLite is the default here (run with `env -u TEST_DATABASE_URL`); on Postgres in CI the
same tests also prove the explicit deletes do not depend on cascade.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.sender import MemoryOtpSender
from app.config import settings
from app.db.models import OtpChallengeRow, StudentRow, UserRow
from tests.conftest import auth_header
from tests.retention.seed import (
    HANDLED,
    NOT_THE_ACCOUNTS,
    account_rows,
    make_account,
    referencing_tables,
)

SECRET_KEY_PARTS = ("hash", "secret", "seed", "password", "pin_", "family_code")
TOKEN_KEYS = {"token", "access_token", "refresh_token", "token_hash"}  # not tokens_in / tokens_out


def _secret(key: str) -> bool:
    lowered = key.lower()
    return lowered in TOKEN_KEYS or any(part in lowered for part in SECRET_KEY_PARTS)


@pytest.fixture
def jobs(tmp_path: Path) -> Path:
    folder = tmp_path / "jobs"
    folder.mkdir()
    settings.engine_jobs_dir = str(folder)
    return folder


def _keys(value: object) -> list[str]:
    if isinstance(value, dict):
        return [str(k) for k in value] + [k for v in value.values() for k in _keys(v)]
    if isinstance(value, list):
        return [k for v in value for k in _keys(v)]
    return []


def test_every_table_that_refers_to_an_account_is_known(db: Session) -> None:
    unknown = set(referencing_tables()) - HANDLED - NOT_THE_ACCOUNTS
    assert not unknown, (
        f"{sorted(unknown)} refer to a student or user. Delete their rows in purge_students "
        "(app/auth/service.py), export them in app/auth/export.py if they hold the learner's "
        "data, then add them to HANDLED in tests/retention/seed.py."
    )


def test_export_has_the_learners_records_and_no_secrets(
    client: TestClient, sender: MemoryOtpSender, db: Session, jobs: Path
) -> None:
    mine = make_account(client, sender, db, "mine@example.com", jobs)
    other = make_account(client, sender, db, "other@example.com", jobs)
    res = client.get("/parents/me/export", headers=auth_header(mine.token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert {s["id"] for s in body["students"]} == {str(i) for i in mine.students}
    assert len(body["learners"]) == 2
    first = body["learners"][0]
    for section in (
        "sessions",
        "answers",
        "mastery",
        "review_cards",
        "lesson_records",
        "misconception_hits",
        "learner_profile",
        "safety_flags",
        "video_jobs",
        "ai_calls",
        "consents",
    ):
        assert first[section], section
    assert first["research"]["checkpoint_results"] and first["research"]["participants"]
    assert first["answers"][0]["payload"] == {"text": "answer-of-mine"}
    text = json.dumps(body)
    # another family's data never appears
    assert "other@example.com" not in text and "answer-of-other" not in text
    assert "topic-other" not in text and "typed-other" not in text
    for sid in other.students:
        assert str(sid) not in text
    # no credential, hash, token or server path
    for key in _keys(body):
        assert not _secret(key), key
    assert str(jobs) not in text and "secret-seed" not in text
    assert "pin_hash" not in first["learner"]


def test_a_second_family_cannot_export_or_delete_the_first(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    mine = make_account(client, sender, db, "mine@example.com")
    other = make_account(client, sender, db, "other@example.com")
    assert (
        client.get(f"/parents/{mine.user_id}/export", headers=auth_header(other.token)).status_code
        == 403
    )
    assert (
        client.delete(f"/parents/{mine.user_id}", headers=auth_header(other.token)).status_code
        == 403
    )


def test_delete_leaves_no_row_in_any_table_that_refers_to_the_account(
    client: TestClient, sender: MemoryOtpSender, db: Session, jobs: Path
) -> None:
    mine = make_account(client, sender, db, "mine@example.com", jobs)
    other = make_account(client, sender, db, "other@example.com", jobs)
    before = account_rows(db, [mine.user_id], mine.students)
    kept_before = account_rows(db, [other.user_id], other.students)
    # every table the models say refers to an account was seeded, so the check below means it
    missing = [t for t in referencing_tables() if t not in NOT_THE_ACCOUNTS and before[t] == 0]
    assert not missing, f"seed a row for {missing} in tests/retention/seed.py"
    assert len(list(jobs.iterdir())) == 4  # two learners each, for two families

    res = client.delete("/parents/me", headers=auth_header(mine.token))
    assert res.status_code == 200, res.text
    db.expire_all()

    after = account_rows(db, [mine.user_id], mine.students)
    assert {t: n for t, n in after.items() if n} == {}
    assert account_rows(db, [other.user_id], other.students) == kept_before
    assert db.scalar(select(OtpChallengeRow).where(OtpChallengeRow.email == mine.email)) is None
    assert db.scalar(select(OtpChallengeRow).where(OtpChallengeRow.email == other.email))
    assert len(list(jobs.iterdir())) == 2  # only the other family's folders remain


def test_a_guest_can_export_and_delete_only_their_own_records(
    client: TestClient, db: Session, sender: MemoryOtpSender
) -> None:
    mine = make_account(client, sender, db, "mine@example.com")
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    other = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    sid = guest["student_id"]
    session = client.post(
        "/sessions",
        json={"student_id": sid, "type": "practice"},
        headers=auth_header(guest["token"]),
    )
    assert session.status_code == 200, session.text

    out = client.get(f"/guest/{sid}/export", headers=auth_header(guest["token"]))
    assert out.status_code == 200, out.text
    assert len(out.json()["learners"][0]["sessions"]) == 1
    for key in _keys(out.json()):
        assert not _secret(key), key

    # another guest's token, a parent's token and no token are all refused
    for headers in (auth_header(other["token"]), auth_header(mine.token), {}):
        assert client.get(f"/guest/{sid}/export", headers=headers).status_code in (401, 403)
        assert client.delete(f"/guest/{sid}", headers=headers).status_code in (401, 403)
    # a signed-in family's learner cannot use the guest route
    kid = str(mine.students[0])
    assert client.delete(f"/guest/{kid}", headers=auth_header(mine.token)).status_code in (401, 403)

    assert client.delete(f"/guest/{sid}", headers=auth_header(guest["token"])).status_code == 200
    db.expire_all()
    assert db.get(StudentRow, uuid.UUID(sid)) is None
    assert db.get(StudentRow, uuid.UUID(other["student_id"])) is not None
    assert db.scalar(select(UserRow).where(UserRow.email == "mine@example.com")) is not None
    assert account_rows(db, [], [uuid.UUID(sid)]) == {
        **{t: 0 for t in referencing_tables()},
        "users": 0,
        "students": 0,
    }
