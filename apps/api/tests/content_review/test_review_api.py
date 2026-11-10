"""The staff review screen's API and the `apply-reviews` command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.content.__main__ import main as content_main
from app.content.validator import load_bundle
from tests.conftest import World, auth_header, seed_user, signup
from tests.content.conftest import content_root, loc, minimal_item, write_yaml  # noqa: F401

LIST = "/staff/review/items"
HINDI = "क्या x = 5 समीकरण x + 7 = 12 हल करता है?"


def _decision(item_id: str) -> str:
    return f"/staff/review/items/{item_id}/decision"


@pytest.fixture
def root(content_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:  # noqa: F811
    mcq = minimal_item("ITEM.Q1", stem="Does x = 5 solve x + 7 = 12?")
    mcq.update(
        type="mcq",
        answer={"sympy": "yes", "accept": ["yes"]},
        options=[{"id": "yes", **loc("Yes")}, {"id": "no", **loc("No")}],
        verify={"kind": "substitution", "equation": "x + 7 = 12", "value": "5"},
        misconception_rules=[{"id": "MC.1", "when_answer_equals": ["no"]}],
    )
    mcq["stem"]["hi"] = HINDI
    mcq["solution_steps"] = [loc("Substitute x = 5."), loc("The correct option is yes.")]
    write_yaml(content_root / "items" / "q1.yaml", mcq)
    monkeypatch.setenv("CONTENT_DIR", str(content_root))
    return content_root


def _hash(client: TestClient, token: str, item_id: str) -> str:
    items = client.get(f"{LIST}?status=all&limit=50", headers=auth_header(token)).json()["items"]
    return next(i for i in items if i["id"] == item_id)["content_hash"]


def _second_teacher(client: TestClient, sender: Any, db: Session) -> str:
    user = seed_user(db, "teacher", "teacher2@example.com")
    return signup(client, sender, user.email)


def test_the_card_shows_the_verified_answer_labels_and_hindi(
    client: TestClient, world: World, root: Path
) -> None:
    out = client.get(f"{LIST}?status=all&limit=50", headers=auth_header(world.teacher_token))
    assert out.status_code == 200, out.text
    cards = {c["id"]: c for c in out.json()["items"]}
    mcq = cards["ITEM.Q1"]
    assert mcq["answer"] == "yes" and mcq["answer_text"] == "Yes"
    assert mcq["verification"]["state"] == "verified"
    assert mcq["wrong_options"] == [
        {"answer": "no", "text": "No", "misconceptions": ["Wrong inverse"]}
    ]
    assert mcq["hindi"]["stem"] == HINDI
    assert mcq["approvals"] == 0 and mcq["approvals_needed"] == 2 and mcq["my_decision"] is None
    assert cards["ITEM.P0"]["verification"]["state"] == "verified"
    assert cards["ITEM.P0"]["hindi"] == {"stem": None, "options": {}}


def test_a_wrong_authored_answer_shows_as_a_mismatch(
    client: TestClient, world: World, root: Path
) -> None:
    path = root / "items" / "p0.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["answer"] = {"sympy": "99", "accept": ["99"]}
    write_yaml(path, data)
    cards = client.get(f"{LIST}?status=all&limit=50", headers=auth_header(world.admin_token))
    card = next(c for c in cards.json()["items"] if c["id"] == "ITEM.P0")
    assert card["verification"]["state"] == "mismatch"


def test_only_teachers_and_admins_reach_it(
    client: TestClient, world: World, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get(LIST).status_code == 401
    assert client.post(_decision("ITEM.Q1"), json={}).status_code == 401
    monkeypatch.delenv("CONTENT_DIR")  # starting a guest needs the real curricula
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    monkeypatch.setenv("CONTENT_DIR", str(root))
    for token in (world.student_token, world.parent_token, guest["token"]):
        head = auth_header(token)
        assert client.get(LIST, headers=head).status_code == 403
        body = {"content_hash": "x", "decision": "approve"}
        assert client.post(_decision("ITEM.Q1"), json=body, headers=head).status_code == 403
    assert client.get(LIST, headers=auth_header(world.admin_token)).status_code == 200


def test_the_reviewer_allowlist_applies_when_set(
    client: TestClient, world: World, root: Path
) -> None:
    from app.config import settings

    settings.reviewer_allowlist = "teacher"  # the part of teacher@example.com before the @
    assert client.get(LIST, headers=auth_header(world.teacher_token)).status_code == 200
    assert client.get(LIST, headers=auth_header(world.admin_token)).status_code == 403


def test_a_stale_hash_is_refused_and_a_note_is_needed(
    client: TestClient, world: World, root: Path
) -> None:
    head = auth_header(world.teacher_token)
    stale = client.post(
        _decision("ITEM.Q1"), json={"content_hash": "0" * 64, "decision": "approve"}, headers=head
    )
    assert stale.status_code == 409
    good = _hash(client, world.teacher_token, "ITEM.Q1")
    for decision in ("reject", "fix"):
        bare = {"content_hash": good, "decision": decision, "note": "  "}
        assert client.post(_decision("ITEM.Q1"), json=bare, headers=head).status_code == 422
    unknown = {"content_hash": good, "decision": "approve"}
    assert client.post(_decision("ITEM.NOPE"), json=unknown, headers=head).status_code == 404


def test_two_distinct_approvals_count_and_a_reviewer_counts_once(
    client: TestClient, world: World, sender: Any, db: Session, root: Path
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    body = {"content_hash": digest, "decision": "approve"}
    first = client.post(_decision("ITEM.Q1"), json=body, headers=auth_header(world.teacher_token))
    assert first.json()["approvals"] == 1
    again = client.post(_decision("ITEM.Q1"), json=body, headers=auth_header(world.teacher_token))
    assert again.json()["approvals"] == 1 and again.json()["my_decision"]["decision"] == "approve"
    second = _second_teacher(client, sender, db)
    done = client.post(_decision("ITEM.Q1"), json=body, headers=auth_header(second))
    assert done.json()["approvals"] == 2
    ready = client.get(f"{LIST}?status=ready", headers=auth_header(second)).json()
    assert [c["id"] for c in ready["items"]] == ["ITEM.Q1"]
    pending = client.get(LIST, headers=auth_header(second)).json()["items"]
    assert "ITEM.Q1" not in {c["id"] for c in pending}


def test_a_reject_blocks_and_a_later_decision_replaces_it(
    client: TestClient, world: World, sender: Any, db: Session, root: Path
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    approve = {"content_hash": digest, "decision": "approve"}
    second = _second_teacher(client, sender, db)
    client.post(_decision("ITEM.Q1"), json=approve, headers=auth_header(world.teacher_token))
    reject = {"content_hash": digest, "decision": "reject", "note": "Option B is not a trap"}
    client.post(_decision("ITEM.Q1"), json=reject, headers=auth_header(second))
    out = client.post(_decision("ITEM.Q1"), json=approve, headers=auth_header(world.admin_token))
    assert out.json()["approvals"] == 2 and out.json()["blocked"] is True
    flagged = client.get(f"{LIST}?status=flagged", headers=auth_header(second)).json()
    assert [c["id"] for c in flagged["items"]] == ["ITEM.Q1"]
    assert flagged["items"][0]["notes"][0]["note"] == "Option B is not a trap"
    client.post(_decision("ITEM.Q1"), json=approve, headers=auth_header(second))  # replaces reject
    back = client.get(f"{LIST}?status=ready", headers=auth_header(second)).json()
    assert [c["id"] for c in back["items"]] == ["ITEM.Q1"]


def test_apply_reviews_writes_two_approvals_and_leaves_the_rest(
    client: TestClient,
    world: World,
    sender: Any,
    db: Session,
    root: Path,
    engine: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second = _second_teacher(client, sender, db)
    first_head, second_head = auth_header(world.teacher_token), auth_header(second)
    for item_id, heads in (("ITEM.Q1", (first_head, second_head)), ("ITEM.P0", (first_head,))):
        digest = _hash(client, world.teacher_token, item_id)
        for head in heads:
            body = {"content_hash": digest, "decision": "approve"}
            assert client.post(_decision(item_id), json=body, headers=head).status_code == 200

    # the in-memory test database exists only on this engine, so hand the command its session
    monkeypatch.setattr(
        "app.db.session.session_factory",
        lambda url=None: sessionmaker(bind=engine, autoflush=False, future=True),
    )
    monkeypatch.delenv("CONTENT_DIR")  # the command validates against the repo's curricula
    assert content_main(["apply-reviews", str(root)]) == 0
    shown = capsys.readouterr().out
    assert "Approved: 1" in shown and "ITEM.Q1" in shown
    assert "Waiting for a second approval: 1" in shown

    items = {i.id: i for i in load_bundle(root).items}
    assert items["ITEM.Q1"].status.value == "approved"
    assert items["ITEM.Q1"].reviewed_by == "teacher2@example.com, teacher@example.com"
    assert items["ITEM.P0"].status.value == "draft"
