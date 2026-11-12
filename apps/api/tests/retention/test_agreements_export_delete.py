"""Export, delete and retention for the role-agreement tables and the new profile fields."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.sender import MemoryOtpSender
from app.config import settings
from app.db.models import AgreementRow, GuardianApprovalRow
from tests.conftest import auth_header
from tests.retention.seed import make_account


@pytest.fixture
def jobs(tmp_path: Path) -> Path:
    folder = tmp_path / "jobs"
    folder.mkdir()
    settings.engine_jobs_dir = str(folder)
    return folder


def test_export_shows_the_agreement_and_a_pending_nickname_but_not_the_contact(
    client: TestClient, sender: MemoryOtpSender, db: Session, jobs: Path
) -> None:
    mine = make_account(client, sender, db, "mine@example.com", jobs)
    body = client.get("/parents/me/export", headers=auth_header(mine.token)).json()
    assert [a["role"] for a in body["agreements"]] == ["guardian"]
    assert body["agreements"][0]["items"] == ["confirm_guardian", "tutoring", "ai_processing"]
    pending = body["learners"][0]["guardian_approval"]
    assert pending and pending[0]["nickname"] == "nick-mine"
    text = json.dumps(body)
    assert "guardian-contact-mine" not in text and "approval-" not in text
    for learner in body["students"]:
        assert {"username", "is_adult", "birth_year"} <= set(learner)


def test_delete_removes_the_agreement_and_the_pending_row(
    client: TestClient, sender: MemoryOtpSender, db: Session, jobs: Path
) -> None:
    mine = make_account(client, sender, db, "mine@example.com", jobs)
    other = make_account(client, sender, db, "other@example.com", jobs)
    assert client.delete("/parents/me", headers=auth_header(mine.token)).status_code == 200
    db.expire_all()
    owners = {row.user_id for row in db.scalars(select(AgreementRow))}
    assert owners == {other.user_id}
    remaining = {r.student_id for r in db.scalars(select(GuardianApprovalRow))}
    assert remaining == {other.students[0]}
