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
        "slip_prone",
        "wheel_spinning",
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


def test_dev_seed_can_reset_only_the_named_scenarios(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    settings.dev_tools = True
    settings.allow_draft_content = True
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert client.post("/dev/seed?only=slip_prone&only=new_student").status_code == 200
    assert calls[-1][-4:] == ["--only", "slip_prone", "--only", "new_student"]
    assert client.post("/dev/seed").status_code == 200
    assert "--only" not in calls[-1]
    assert client.post("/dev/seed?only=nope").status_code == 400


def test_dev_item_answer_is_404_without_dev_tools(client: TestClient) -> None:
    assert client.get("/dev/items/ANY/answer").status_code == 404


def test_dev_item_answer_returns_the_authored_key(client: TestClient, db: Session) -> None:
    from app.db.models import ItemRow
    from tests.player.test_skip_ahead_api import _item

    settings.dev_tools = True
    settings.allow_draft_content = True
    db.add(_item("DEV.ANS.1", "6", role="procedure"))
    db.commit()
    body = client.get("/dev/items/DEV.ANS.1/answer").json()
    assert body == {"id": "DEV.ANS.1", "answer": "6", "accept": ["6", "x=6"]}
    assert client.get("/dev/items/NOPE/answer").status_code == 404
    assert db.get(ItemRow, "DEV.ANS.1") is not None


def test_allowed_origins_include_localhost_and_configured_lan_origins() -> None:
    base = allowed_origins("")
    assert "http://localhost:3000" in base and "http://127.0.0.1:3001" in base
    extra = allowed_origins(" http://192.168.1.20:3000 ,http://pc.local:3000,, ")
    assert "http://192.168.1.20:3000" in extra and "http://pc.local:3000" in extra
    assert set(base) < set(extra)


def test_wildcard_origin_is_rejected() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        allowed_origins("*")


def test_seed_endpoint_is_404_unless_dev_tools(client: TestClient) -> None:
    assert client.post("/dev/seed").status_code == 404


def test_seed_endpoint_runs_the_cli_in_a_subprocess(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess
    import sys

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, 0, stdout="seeded 5\n", stderr="")

    monkeypatch.setattr("app.dev.router.subprocess.run", fake_run)
    settings.dev_tools = True
    settings.allow_draft_content = True
    response = client.post("/dev/seed")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "output": "seeded 5\n"}
    assert calls == [[sys.executable, "-m", "app.dev", "seed_scenarios"]]


def test_seed_endpoint_reports_a_failed_seed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="ERROR: no content")

    monkeypatch.setattr("app.dev.router.subprocess.run", fake_run)
    settings.dev_tools = True
    settings.allow_draft_content = True
    response = client.post("/dev/seed")
    assert response.status_code == 500
    assert "no content" in response.json()["detail"]
