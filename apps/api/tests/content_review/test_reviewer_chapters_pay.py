"""Reviewer desk slice 4: class / subject / chapter groups and filters, and the pay statement."""

# ruff: noqa: F811
from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ContentReviewRow
from tests.conftest import World, auth_header, seed_user
from tests.content.conftest import (  # noqa: F401
    content_root,
    loc,
    minimal_item,
    minimal_skill,
    write_yaml,
)
from tests.content_review.test_review_api import LIST, _decision, root  # noqa: F401
from tests.content_review.test_reviewer_desk import YES, _approve, _hash, _invite, _post, desk  # noqa: F401

CHAPTERS = "/staff/review/chapters"
PAY = "/staff/review/pay-statement"


@pytest.fixture
def two_chapters(root: Path) -> Path:
    """The base content (class 9, chapter `ov1`, subject unknown) plus a class 10 maths chapter
    with curriculum metadata, a class 10 physics chapter known only by its overlay, and a skill
    that no overlay lists."""
    write_yaml(
        root / "curricula" / "cbse" / "curriculum.yaml",
        {
            "id": "cbse",
            "books": [
                {
                    "id": "cbse.10.maths",
                    "grade": 10,
                    "subject": "maths",
                    "chapters": [
                        {
                            "id": "cbse.10.maths.quad",
                            "overlay_id": "cbse.10.maths.quad",
                            "titles": {"en": "Quadratic Equations"},
                        }
                    ],
                }
            ],
        },
    )
    for skill, overlay, chapter in (
        ("MATH.QUAD", "cbse.10.maths.quad", "quadratic_equations"),
        ("PHY.HEAT", "cbse.10.physics.heat", "heat"),
    ):
        write_yaml(root / "skills" / f"{skill}.yaml", minimal_skill(skill))
        write_yaml(
            root / "overlays" / f"{overlay}.yaml",
            {
                "id": overlay,
                "curriculum_id": "cbse",
                "grade": 10,
                "chapter": chapter,
                "skill_ids": [skill],
                "live": False,
            },
        )
    for item_id, skill in (
        ("ITEM.X1", "MATH.QUAD"),
        ("ITEM.X2", "MATH.QUAD"),
        ("ITEM.H1", "PHY.HEAT"),
        ("ITEM.Z1", "MATH.NOWHERE"),
    ):
        write_yaml(root / "items" / f"{item_id}.yaml", minimal_item(item_id, skill=skill))
    return root


def _groups(client: TestClient, token: str) -> dict[str, dict[str, Any]]:
    out = client.get(CHAPTERS, headers=auth_header(token))
    assert out.status_code == 200, out.text
    return {g["chapter"]: g for g in out.json()["groups"]}


def _ids(client: TestClient, token: str, query: str) -> list[str]:
    out = client.get(f"{LIST}?status=all&limit=50&{query}", headers=auth_header(token))
    assert out.status_code == 200, out.text
    return [c["id"] for c in out.json()["items"]]


# ---- chapters and filters ----


def test_chapters_list_what_exists_with_metadata_and_report_gaps(
    client: TestClient, world: World, two_chapters: Path, desk: None
) -> None:
    out = client.get(CHAPTERS, headers=auth_header(world.teacher_token)).json()
    groups = {g["chapter"]: g for g in out["groups"]}
    assert set(groups) == {"ov1", "cbse.10.maths.quad", "cbse.10.physics.heat", "unmapped"}
    quad = groups["cbse.10.maths.quad"]
    assert (quad["class"], quad["subject"], quad["title"], quad["total"], quad["pending"]) == (
        10,
        "maths",
        "Quadratic Equations",
        2,
        2,
    )
    assert quad["in_curriculum"] is True
    heat = groups["cbse.10.physics.heat"]
    assert (heat["class"], heat["subject"], heat["title"]) == (10, "physics", "Heat")
    assert heat["in_curriculum"] is False  # named only by its overlay
    assert groups["unmapped"]["class"] is None and groups["unmapped"]["total"] == 1
    assert groups["ov1"]["class"] == 9 and groups["ov1"]["total"] == 9  # Q1, P0-P4, D0-D2
    # nothing is listed for a class or subject without content
    assert {g["class"] for g in out["groups"]} <= {9, 10, None}
    assert "chemistry" not in {g["subject"] for g in out["groups"]}
    assert set(out["chapters_without_curriculum_entry"]) == {
        "cbse.10.physics.heat",
        "ov1",
        "unmapped",
    }
    # ordered by class, then subject, then title, with the unmapped group last
    assert [g["chapter"] for g in out["groups"]][-1] == "unmapped"


def test_list_filters_by_class_subject_and_chapter(
    client: TestClient, world: World, two_chapters: Path, desk: None
) -> None:
    token = world.teacher_token
    assert _ids(client, token, "class=10&subject=maths") == ["ITEM.X1", "ITEM.X2"]
    assert _ids(client, token, "class=10") == ["ITEM.H1", "ITEM.X1", "ITEM.X2"]
    assert _ids(client, token, "chapter=cbse.10.physics.heat") == ["ITEM.H1"]
    assert _ids(client, token, "class=9&subject=maths") == []
    assert _ids(client, token, "chapter=unmapped") == ["ITEM.Z1"]
    assert _ids(client, token, "class=12") == []
    everything = _ids(client, token, "")
    assert len(everything) == 13 and "ITEM.Z1" in everything
    total = client.get(f"{LIST}?status=all&class=10&subject=maths", headers=auth_header(token))
    assert total.json()["total"] == 2
    bad = client.get(f"{LIST}?class=abc", headers=auth_header(token))
    assert bad.status_code == 422


def test_pending_counts_do_not_reveal_how_others_voted(
    client: TestClient, world: World, sender: Any, two_chapters: Path, desk: None
) -> None:
    _, outside = _invite(client, world, sender, "outside@example.com")
    cards = client.get(f"{LIST}?class=10&subject=maths&status=all", headers=auth_header(outside))
    by_id = {c["id"]: c["content_hash"] for c in cards.json()["items"]}
    before = _groups(client, world.teacher_token)["cbse.10.maths.quad"]
    # the outside reviewer approves one item and rejects the other
    assert _post(client, outside, _approve(by_id["ITEM.X1"]), "ITEM.X1").status_code == 200
    reject = {
        "content_hash": by_id["ITEM.X2"],
        "decision": "reject",
        "severity": "blocker",
        "reason_code": "1",
        "note": "The answer is wrong for this question",
    }
    assert _post(client, outside, reject, "ITEM.X2").status_code == 200
    # the teacher has decided nothing, so the group still shows 2 pending: no vote is visible
    assert _groups(client, world.teacher_token)["cbse.10.maths.quad"] == before
    # the teacher's pending count drops only by the teacher's own decision
    assert (
        _post(client, world.teacher_token, _approve(by_id["ITEM.X1"]), "ITEM.X1").status_code == 200
    )
    after = _groups(client, world.teacher_token)["cbse.10.maths.quad"]
    assert (after["total"], after["pending"]) == (2, 1)
    # the filtered list agrees with the group count
    pending = client.get(
        f"{LIST}?class=10&subject=maths&status=pending", headers=auth_header(world.teacher_token)
    )
    assert pending.json()["total"] == 1


def test_chapters_and_filters_need_the_desk_and_a_reviewer(
    client: TestClient, world: World, two_chapters: Path
) -> None:
    assert client.get(CHAPTERS, headers=auth_header(world.teacher_token)).status_code == 404
    refused = client.get(f"{LIST}?class=10", headers=auth_header(world.teacher_token))
    assert refused.status_code == 422
    assert client.get(LIST, headers=auth_header(world.teacher_token)).status_code == 200
    settings.reviewer_desk_enabled = True
    assert client.get(CHAPTERS).status_code == 401
    for token in (world.parent_token, world.student_token):
        assert client.get(CHAPTERS, headers=auth_header(token)).status_code == 403


# ---- pay statement ----


def _row(
    reviewer: uuid.UUID,
    item: str,
    decision: str,
    when: str,
    seconds: int | None = None,
    content_hash: str = "h" * 64,
) -> ContentReviewRow:
    return ContentReviewRow(
        id=uuid.uuid4(),
        item_id=item,
        content_hash=content_hash,
        reviewer_id=reviewer,
        reviewer_label="x",
        decision=decision,
        created_at=datetime.fromisoformat(when).replace(tzinfo=UTC),
        active_seconds=seconds,
    )


def _statement(client: TestClient, world: World, query: str) -> dict[str, Any]:
    out = client.get(f"{PAY}?{query}", headers=auth_header(world.admin_token))
    assert out.status_code == 200, out.text
    return out.json()


def test_the_pay_statement_counts_each_standing_paid_decision_once(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rv = seed_user(db, "reviewer", "rv@example.com")
    rows = [
        _row(rv.id, "I1", "approve", "2026-03-02T10:00", 60),
        _row(rv.id, "I2", "fix", "2026-03-02T10:05", 40),
        _row(rv.id, "I3", "skip", "2026-03-02T10:10", 5),
        # approved then withdrew and never decided again: not paid
        _row(rv.id, "I4", "approve", "2026-03-03T09:00", 10),
        _row(rv.id, "I4", "withdraw", "2026-03-03T09:05"),
        # withdrew and decided again: paid once
        _row(rv.id, "I5", "approve", "2026-03-03T09:10", 20),
        _row(rv.id, "I5", "withdraw", "2026-03-03T09:11"),
        _row(rv.id, "I5", "approve", "2026-03-03T09:12", 15),
        # changed their mind: one decision, the standing one (reject)
        _row(rv.id, "I6", "approve", "2026-03-04T09:00", 30),
        _row(rv.id, "I6", "reject", "2026-03-04T09:30", 30),
    ]
    db.add_all(rows)
    db.commit()
    out = _statement(client, world, "from=2026-03-01&to=2026-03-31")
    assert (
        out["rate_inr"] == 30 and out["monthly_cap_inr"] == 4000 and out["cap_month"] == "2026-03"
    )
    assert out["quality_multiplier"] is None
    (me,) = out["reviewers"]
    assert me["email"] == "rv@example.com" and me["label"].startswith("R-")
    assert me["reviewer_id"] == str(rv.id)
    assert me["paid_decisions"] == 4
    assert me["decisions"] == {"approve": 2, "fix": 1, "reject": 1}  # I1, I5 / I2 / I6
    assert me["active_seconds"] == 60 + 40 + 5 + 10 + 20 + 15 + 30 + 30
    assert me["changed_after_seeing"] == 2  # I5's second approve and I6's reject
    assert me["amount_inr"] == 120 and me["amount_before_cap_inr"] == 120
    assert me["cap_applied"] is False
    assert out["total_paid_decisions"] == 4 and out["total_amount_inr"] == 120
    # the rate parameter overrides the setting for one request only
    assert (
        _statement(client, world, "from=2026-03-01&to=2026-03-31&rate=50")["reviewers"][0][
            "amount_inr"
        ]
        == 200
    )
    assert (
        _statement(client, world, "from=2026-03-01&to=2026-03-31")["reviewers"][0]["amount_inr"]
        == 120
    )
    settings.review_rate_per_decision_inr = 45
    assert _statement(client, world, "from=2026-03-01&to=2026-03-31")["rate_inr"] == 45


def test_a_decision_changed_in_a_later_month_is_not_paid_again(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rv = seed_user(db, "reviewer", "rv@example.com")
    db.add_all(
        [
            _row(rv.id, "I1", "approve", "2026-02-20T10:00", 10),
            _row(rv.id, "I1", "reject", "2026-03-05T10:00", 10),
            _row(rv.id, "I2", "approve", "2026-03-06T10:00", 10),
        ]
    )
    db.commit()
    feb = _statement(client, world, "from=2026-02-01&to=2026-02-28")["reviewers"][0]
    assert feb["paid_decisions"] == 1  # the type shown is the standing one (reject)
    mar = _statement(client, world, "from=2026-03-01&to=2026-03-31")["reviewers"][0]
    assert mar["paid_decisions"] == 1  # only I2; I1 was paid in February
    assert mar["active_seconds"] == 20
    nothing = _statement(client, world, "from=2025-01-01&to=2025-01-31")
    assert nothing["reviewers"] == [] and nothing["total_amount_inr"] == 0


def test_the_monthly_cap_applies_to_the_month_of_the_end_date(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    settings.review_monthly_cap_inr = 100
    rv = seed_user(db, "reviewer", "rv@example.com")
    other = seed_user(db, "reviewer", "second.rv@example.com")
    db.add_all(
        [_row(rv.id, f"A{n}", "approve", f"2026-03-0{n}T10:00") for n in range(1, 6)]
        + [_row(other.id, "A1", "approve", "2026-03-01T10:00")]
        # three decisions in the first half of March, five in the second half
        + [_row(rv.id, f"B{n}", "approve", "2026-03-20T10:00") for n in range(1, 4)]
    )
    db.commit()
    first = _statement(client, world, "from=2026-03-01&to=2026-03-15")
    by_email = {r["email"]: r for r in first["reviewers"]}
    capped = by_email["rv@example.com"]
    assert capped["amount_before_cap_inr"] == 150 and capped["amount_inr"] == 100
    assert capped["cap_applied"] is True
    assert by_email["second.rv@example.com"]["cap_applied"] is False
    assert by_email["second.rv@example.com"]["amount_inr"] == 30
    # the second half-month statement counts what the first one already paid
    second = _statement(client, world, "from=2026-03-16&to=2026-03-31")
    (late,) = [r for r in second["reviewers"] if r["email"] == "rv@example.com"]
    assert late["paid_decisions"] == 3 and late["amount_before_cap_inr"] == 90
    assert late["amount_inr"] == 0 and late["cap_applied"] is True  # 5 x 30 > 100 already
    # a range ending in April does not cap its March decisions (they are not in `to`'s month)
    spanning = _statement(client, world, "from=2026-03-01&to=2026-04-02")
    (span,) = [r for r in spanning["reviewers"] if r["email"] == "rv@example.com"]
    assert span["cap_applied"] is False and span["amount_inr"] == 240
    assert spanning["cap_month"] == "2026-04"


def test_the_pay_statement_as_csv_and_who_may_read_it(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rv = seed_user(db, "reviewer", "rv@example.com")
    db.add(_row(rv.id, "I1", "approve", "2026-03-02T10:00", 60))
    db.commit()
    out = client.get(
        f"{PAY}?from=2026-03-01&to=2026-03-31&format=csv", headers=auth_header(world.admin_token)
    )
    assert out.status_code == 200
    assert out.headers["content-type"].startswith("text/csv")
    assert "pay-statement-2026-03-01-2026-03-31.csv" in out.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(out.text)))
    assert len(rows) == 1
    assert rows[0]["email"] == "rv@example.com" and rows[0]["amount_inr"] == "30.0"
    assert rows[0]["approve"] == "1" and rows[0]["paid_decisions"] == "1"
    assert not any("upi" in c.lower() or "bank" in c.lower() for c in rows[0])
    url = f"{PAY}?from=2026-03-01&to=2026-03-31"
    for token in (world.teacher_token, world.parent_token, world.student_token):
        assert client.get(url, headers=auth_header(token)).status_code == 403
    assert client.get(url).status_code == 401
    bad = client.get(f"{PAY}?from=2026-03-31&to=2026-03-01", headers=auth_header(world.admin_token))
    assert bad.status_code == 422
    negative = client.get(f"{url}&rate=-1", headers=auth_header(world.admin_token))
    assert negative.status_code == 422
    unknown = client.get(f"{url}&format=xml", headers=auth_header(world.admin_token))
    assert unknown.status_code == 422


def test_the_pay_statement_is_off_with_the_desk_off(client: TestClient, world: World) -> None:
    url = f"{PAY}?from=2026-03-01&to=2026-03-31"
    assert client.get(url, headers=auth_header(world.admin_token)).status_code == 404


# ---- status=todo: only what the caller has not decided on the current content ----


def _todo(client: TestClient, token: str, query: str = "") -> dict[str, Any]:
    out = client.get(f"{LIST}?status=todo&limit=50&{query}", headers=auth_header(token))
    assert out.status_code == 200, out.text
    return out.json()


def _todo_ids(client: TestClient, token: str) -> set[str]:
    return {c["id"] for c in _todo(client, token)["items"]}


def _digest(client: TestClient, token: str, item_id: str) -> str:
    return next(c["content_hash"] for c in _todo(client, token)["items"] if c["id"] == item_id)


def test_todo_lists_only_undecided_and_matches_the_chapter_count(
    client: TestClient, world: World, two_chapters: Path, desk: None
) -> None:
    token = world.teacher_token
    assert _todo(client, token)["total"] == 13
    digest = _digest(client, token, "ITEM.X1")
    assert _post(client, token, _approve(digest), item="ITEM.X1").status_code == 200
    after = _todo(client, token)
    assert "ITEM.X1" not in {c["id"] for c in after["items"]} and after["total"] == 12
    # the picker count and the todo list agree, per chapter and overall
    groups = _groups(client, token)
    quad = _todo(client, token, "chapter=cbse.10.maths.quad")["total"]
    assert groups["cbse.10.maths.quad"]["pending"] == quad == 1
    assert sum(g["pending"] for g in groups.values()) == after["total"]
    # the old values behave as before: the approved item is still there under "all"
    assert "ITEM.X1" in _ids(client, token, "")


def test_todo_skip_does_not_exclude_and_withdraw_includes_again(
    client: TestClient, world: World, two_chapters: Path, desk: None
) -> None:
    token = world.teacher_token
    digest = _digest(client, token, "ITEM.X1")
    _post(client, token, {"content_hash": digest, "decision": "skip"}, item="ITEM.X1")
    assert "ITEM.X1" in _todo_ids(client, token)
    _post(client, token, _approve(digest), item="ITEM.X1")
    assert "ITEM.X1" not in _todo_ids(client, token)
    _post(client, token, {"content_hash": digest, "decision": "withdraw"}, item="ITEM.X1")
    assert "ITEM.X1" in _todo_ids(client, token)


def test_todo_ignores_other_reviewers_and_stays_blind(
    client: TestClient, world: World, sender: Any, db: Session, two_chapters: Path, desk: None
) -> None:
    from tests.content_review.test_review_api import _second_teacher

    second = _second_teacher(client, sender, db)
    digest = _digest(client, second, "ITEM.X1")
    _post(client, world.teacher_token, _approve(digest), item="ITEM.X1")
    _post(client, world.admin_token, _approve(digest), item="ITEM.X1")
    mine = _todo(client, second)
    card = next(c for c in mine["items"] if c["id"] == "ITEM.X1")
    # two others approved, yet it is still to do for me, and nothing shows how they voted
    assert card["approvals"] is None and card["others"] == [] and card["my_decision"] is None
    assert mine["total"] == 13 and set(mine) == {"total", "offset", "items"}
    # and the two who approved no longer see it
    assert "ITEM.X1" not in _todo_ids(client, world.teacher_token)


def test_an_edited_item_is_to_do_again(
    client: TestClient, world: World, two_chapters: Path, desk: None
) -> None:
    token = world.teacher_token
    digest = _digest(client, token, "ITEM.X1")
    _post(client, token, _approve(digest), item="ITEM.X1")
    path = two_chapters / "items" / "ITEM.X1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("Solve for x", "Work out x"), "utf-8")
    again = {c["id"]: c for c in _todo(client, token)["items"]}
    assert again["ITEM.X1"]["content_hash"] != digest


def test_todo_pages_by_offset_without_overlap(
    client: TestClient, world: World, two_chapters: Path, desk: None
) -> None:
    token = world.teacher_token
    first = client.get(f"{LIST}?status=todo&limit=5", headers=auth_header(token)).json()
    for card in first["items"]:
        _post(client, token, _approve(card["content_hash"]), item=card["id"])
    nxt = client.get(f"{LIST}?status=todo&limit=5", headers=auth_header(token)).json()
    assert not {c["id"] for c in first["items"]} & {c["id"] for c in nxt["items"]}
    assert nxt["total"] == first["total"] - 5


def test_todo_needs_the_desk_and_the_old_values_are_unchanged(
    client: TestClient, world: World, two_chapters: Path
) -> None:
    settings.reviewer_desk_enabled = False
    head = auth_header(world.teacher_token)
    assert client.get(f"{LIST}?status=todo", headers=head).status_code == 422
    assert client.get(f"{LIST}?status=pending", headers=head).status_code == 200
