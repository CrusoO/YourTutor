from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import StudentRow
from app.main import allowed_origins
from tests.conftest import World


def test_dev_scenarios_are_404_by_default(client: TestClient) -> None:
    assert client.get("/dev/scenarios").status_code == 404


def test_dev_scenarios_need_both_flags(client: TestClient) -> None:
    settings.dev_tools = True
    settings.allow_draft_content = False
    assert client.get("/dev/scenarios").status_code == 404
    settings.dev_tools = False
    settings.allow_draft_content = True
    assert client.get("/dev/scenarios").status_code == 404


def test_dev_scenarios_list_credentials_and_seeded_flag(
    client: TestClient, world: World, db: Session
) -> None:
    settings.dev_tools = True
    settings.allow_draft_content = True
    body = client.get("/dev/scenarios").json()
    assert [row["name"] for row in body["scenarios"]] == [
        "new_student",
        "mid_chapter",
        "skill_at_level_4",
        "review_due",
        "all_skills_level_4",
    ]
    assert all(row["pin"] == "1234" and row["family_code"] for row in body["scenarios"])
    assert not any(row["seeded"] for row in body["scenarios"])
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.family_code = "DEVNEW"
    db.commit()
    seeded = {
        row["name"]: row["seeded"] for row in client.get("/dev/scenarios").json()["scenarios"]
    }
    assert seeded["new_student"] is True and seeded["mid_chapter"] is False


def test_allowed_origins_include_localhost_and_configured_lan_origins() -> None:
    base = allowed_origins("")
    assert "http://localhost:3000" in base and "http://127.0.0.1:3001" in base
    extra = allowed_origins(" http://192.168.1.20:3000 ,http://pc.local:3000,, ")
    assert "http://192.168.1.20:3000" in extra and "http://pc.local:3000" in extra
    assert set(base) < set(extra)


def test_wildcard_origin_is_rejected() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        allowed_origins("*")
