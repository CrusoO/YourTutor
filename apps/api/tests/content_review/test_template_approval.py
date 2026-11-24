"""Reviewer desk slice 7: template-level approval (records and queue only)."""

# ruff: noqa: F811
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.content.labels import (
    REVIEWED_BADGE,
    TEMPLATE_REVIEWED_BADGE,
    item_labels,
)
from app.content.schema import Item
from app.content_review import service, templates
from tests.conftest import World, auth_header
from tests.content.conftest import content_root, minimal_item, write_yaml  # noqa: F401
from tests.content_review.test_review_api import LIST, root  # noqa: F401
from tests.content_review.test_reviewer_desk import (  # noqa: F401
    _approve,
    _decision,
    _fix,
    _invite,
    _post,
    desk,
)

SUMMARY = "/staff/review/templates/summary"
CHAPTERS = "/staff/review/chapters"
MATHS = ("TPL.C10.X", "hash-x", "factory-2")
SMALL = ("TPL.C10.SMALL", "hash-small", "factory-2")
PHYS = ("TPL2.PHY.ELEC", "hash-phys", "factory-2")
T_SAMPLES = ("ITEM.T1", "ITEM.T4", "ITEM.T6")
UNTEMPLATED = {f"ITEM.P{i}" for i in range(5)} | {f"ITEM.D{i}" for i in range(3)}


def _tpl_item(item_id: str, tpl: tuple[str, str, str], difficulty: float) -> dict[str, Any]:
    data = minimal_item(item_id)
    data.update(
        difficulty=difficulty,
        template_id=tpl[0],
        template_hash=tpl[1],
        generator_version=tpl[2],
    )
    return data


def _write_maths(root: Path, tpl: tuple[str, str, str], stem: str | None = None) -> None:
    for n in range(1, 7):
        data = _tpl_item(f"ITEM.T{n}", tpl, n / 10)
        if stem:  # a regenerated question: its text, and so its content hash, differs
            data["stem"] = {"en": f"{stem} ({n})"}
        write_yaml(root / "items" / f"t{n}.yaml", data)


@pytest.fixture
def tpl_root(content_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:  # noqa: F811
    """The base content (8 untemplated drafts) plus MATHS with 6 items (difficulties 0.1 to 0.6,
    samples T1, T4, T6), SMALL with 2 and PHYS with 4."""
    _write_maths(content_root, MATHS)
    for n in (1, 2):
        write_yaml(content_root / "items" / f"s{n}.yaml", _tpl_item(f"ITEM.S{n}", SMALL, n / 10))
    for n in range(1, 5):
        write_yaml(content_root / "items" / f"y{n}.yaml", _tpl_item(f"ITEM.Y{n}", PHYS, n / 10))
    monkeypatch.setenv("CONTENT_DIR", str(content_root))
    return content_root


@pytest.fixture
def tmode(desk: None) -> None:
    settings.review_template_approval_enabled = True
    settings.review_template_double_review_percent = 0


def _cards(client: TestClient, token: str, status: str = "todo") -> dict[str, dict[str, Any]]:
    out = client.get(f"{LIST}?status={status}&limit=50", headers=auth_header(token))
    assert out.status_code == 200, out.text
    return {c["id"]: c for c in out.json()["items"]}


def _approve_item(client: TestClient, token: str, item_id: str) -> None:
    digest = _cards(client, token, "all")[item_id]["content_hash"]
    assert _post(client, token, _approve(digest), item_id).status_code == 200


def _approve_samples(client: TestClient, token: str, ids: tuple[str, ...]) -> None:
    for item_id in ids:
        _approve_item(client, token, item_id)


def _state(client: TestClient, world: World, template_id: str) -> dict[str, Any]:
    out = client.get(
        f"/staff/review/templates/{template_id}", headers=auth_header(world.admin_token)
    )
    assert out.status_code == 200, out.text
    return out.json()["versions"][0]


# ---- pure rules ----


def _items(difficulties: list[float]) -> list[Item]:
    out = []
    for n, d in enumerate(difficulties):
        data = minimal_item(f"I{n}")
        data["difficulty"] = d
        out.append(Item.model_validate(data))
    return out


def test_samples_are_deterministic_easiest_middle_hardest() -> None:
    items = _items([0.9, 0.1, 0.5, 0.3, 0.7, 0.2])  # by difficulty: I1 I5 I3 I2 I4 I0
    first = templates.sample_ids(items)
    assert first == ["I1", "I2", "I0"]  # easiest, index 3 of 6, hardest
    assert templates.sample_ids(reversed(items)) == first
    assert templates.sample_ids(items) == first


def test_fewer_than_three_items_are_all_samples_and_ties_break_by_id() -> None:
    assert templates.sample_ids(_items([0.4])) == ["I0"]
    assert templates.sample_ids(_items([0.5, 0.2])) == ["I1", "I0"]
    assert templates.sample_ids(_items([0.3, 0.3, 0.3, 0.3])) == ["I0", "I2", "I3"]
    assert len(templates.sample_ids(_items([0.1, 0.2, 0.3]))) == 3


def _bucket(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16) % 100


def test_required_approvals_family_and_hash_share() -> None:
    settings.review_template_double_review_percent = 0
    assert templates.required_approvals("TPL2.PHY.ELEC", "h") == 2
    assert templates.required_approvals("TPL2.CHEM.ACIDS", "h") == 2
    assert templates.required_approvals("TPL2.BIO.CELL", "h") == 2
    assert templates.required_approvals("TPL2.PHYSICS", "h") == 1  # not a dot-boundary match
    settings.review_template_double_review_percent = 15
    low = next(h for h in (f"h{n}" for n in range(500)) if _bucket(h) < 15)
    high = next(h for h in (f"h{n}" for n in range(500)) if _bucket(h) >= 15)
    assert templates.required_approvals("TPL.C10.AP", low) == 2
    assert templates.required_approvals("TPL.C10.AP", high) == 1
    assert templates.required_approvals("TPL.C10.AP", low) == 2  # same answer every time
    settings.review_template_double_review_percent = 0
    assert templates.required_approvals("TPL.C10.AP", low) == 1
    settings.review_template_double_review_percent = 100
    assert templates.required_approvals("TPL.C10.AP", high) == 2
    settings.review_template_double_review_percent = 0
    settings.review_template_approvals_required = 2
    assert templates.required_approvals("TPL.C10.AP", high) == 2


def test_the_two_labels_are_distinct_and_name_no_board() -> None:
    assert TEMPLATE_REVIEWED_BADGE == "Question type reviewed by a teacher"
    individual = item_labels(pool="practice", tier="A", original=True, pattern=None, reviewed=True)
    assert individual is not None and individual["reviewed"] == REVIEWED_BADGE
    covered = item_labels(
        pool="practice",
        tier="A",
        original=True,
        pattern=None,
        reviewed=False,
        template_reviewed=True,
    )
    assert covered is not None and covered["reviewed"] == TEMPLATE_REVIEWED_BADGE
    plain = item_labels(pool="practice", tier="A", original=True, pattern=None, reviewed=False)
    assert plain is not None and "reviewed" not in plain
    both = item_labels(
        pool="practice",
        tier="A",
        original=True,
        pattern=None,
        reviewed=True,
        template_reviewed=True,
    )
    assert both is not None and both["reviewed"] == REVIEWED_BADGE


# ---- derived approval ----


def test_approving_all_samples_makes_the_template_ready(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    token = world.teacher_token
    assert _state(client, world, MATHS[0])["state"] == "in_review"
    _approve_samples(client, token, T_SAMPLES[:2])
    partial = _state(client, world, MATHS[0])
    assert partial["state"] == "in_review" and partial["approvals"] == 0
    assert partial["reviewers"][0]["approved_samples"] == 2
    _approve_item(client, token, "ITEM.T6")
    ready = _state(client, world, MATHS[0])
    assert ready["state"] == "ready" and ready["approvals"] == 1
    assert ready["approvals_needed"] == 1
    assert [s["item_id"] for s in ready["samples"]] == list(T_SAMPLES)


def test_a_withdrawn_sample_voids_the_approval_and_a_skip_does_not_count(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    token = world.teacher_token
    _approve_samples(client, token, T_SAMPLES)
    digest = _cards(client, token, "all")["ITEM.T4"]["content_hash"]
    withdrawn = _post(client, token, {"content_hash": digest, "decision": "withdraw"}, "ITEM.T4")
    assert withdrawn.status_code == 200
    assert _state(client, world, MATHS[0])["state"] == "in_review"
    skipped = _post(client, token, {"content_hash": digest, "decision": "skip"}, "ITEM.T4")
    assert skipped.status_code == 200
    assert _state(client, world, MATHS[0])["approvals"] == 0
    assert _post(client, token, _approve(digest), "ITEM.T4").status_code == 200
    assert _state(client, world, MATHS[0])["state"] == "ready"


def test_an_item_that_is_not_a_sample_does_not_count_toward_approval(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    _approve_samples(client, world.teacher_token, ("ITEM.T1", "ITEM.T2", "ITEM.T3", "ITEM.T6"))
    assert _state(client, world, MATHS[0])["state"] == "in_review"


def test_small_templates_use_every_item_as_a_sample(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    _approve_samples(client, world.teacher_token, ("ITEM.S1", "ITEM.S2"))
    version = _state(client, world, SMALL[0])
    assert version["state"] == "ready" and len(version["samples"]) == 2


# ---- required approvals ----


def test_a_physics_template_needs_two_reviewers(
    client: TestClient, world: World, sender: Any, tpl_root: Path, tmode: None
) -> None:
    ids = ("ITEM.Y1", "ITEM.Y3", "ITEM.Y4")  # difficulties .1 .3 .4: easiest, index 2, hardest
    _approve_samples(client, world.teacher_token, ids)
    one = _state(client, world, PHYS[0])
    assert (one["state"], one["approvals"], one["approvals_needed"]) == ("in_review", 1, 2)
    assert one["double_review"] is True
    _, outside = _invite(client, world, sender, "outside@example.com")
    _approve_samples(client, outside, ids)
    assert _state(client, world, PHYS[0])["state"] == "ready"


def test_the_share_setting_makes_a_maths_template_need_two(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    settings.review_template_double_review_percent = 100
    _approve_samples(client, world.teacher_token, T_SAMPLES)
    version = _state(client, world, MATHS[0])
    assert version["approvals_needed"] == 2 and version["state"] == "in_review"


# ---- queue ----


def test_the_queue_lists_samples_and_untemplated_items_only(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    token = world.teacher_token
    todo = set(_cards(client, token))
    samples = {"ITEM.S1", "ITEM.S2", "ITEM.Y1", "ITEM.Y3", "ITEM.Y4", *T_SAMPLES}
    assert todo == samples | UNTEMPLATED
    cards = _cards(client, token)
    assert cards["ITEM.T4"]["template"] == {
        "template_id": "TPL.C10.X",
        "sample_index": 2,
        "sample_count": 3,
        "questions": 6,
    }
    assert cards["ITEM.P0"]["template"] is None
    _approve_item(client, token, "ITEM.T4")  # my own decision leaves my queue
    assert "ITEM.T4" not in _cards(client, token)


def test_flag_off_is_exactly_item_level(
    client: TestClient, world: World, tpl_root: Path, desk: None
) -> None:
    cards = _cards(client, world.teacher_token)
    assert len(cards) == 20 and all("template" not in c for c in cards.values())
    assert all(c["approvals_needed"] == 2 for c in cards.values())
    groups = client.get(CHAPTERS, headers=auth_header(world.teacher_token)).json()
    assert "template_mode" not in groups
    assert all("templates_pending" not in g for g in groups["groups"])
    for path in (SUMMARY, "/staff/review/templates/TPL.C10.X"):
        assert client.get(path, headers=auth_header(world.admin_token)).status_code == 404


def test_the_flag_needs_the_desk(client: TestClient, world: World, tpl_root: Path) -> None:
    settings.review_template_approval_enabled = True
    assert client.get(SUMMARY, headers=auth_header(world.admin_token)).status_code == 404
    assert not templates.template_mode()


def test_the_picker_counts_samples_and_question_types(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    def ov1() -> dict[str, Any]:
        out = client.get(CHAPTERS, headers=auth_header(world.teacher_token)).json()
        assert out["template_mode"] is True
        return next(g for g in out["groups"] if g["chapter"] == "ov1")

    first = ov1()
    assert first["total"] == 20
    assert first["pending"] == 16  # 8 samples and 8 untemplated items
    assert first["templates_pending"] == 3
    _approve_samples(client, world.teacher_token, ("ITEM.S1", "ITEM.S2"))
    after = ov1()
    assert (after["pending"], after["templates_pending"]) == (14, 2)


# ---- block and escalate ----


def test_a_fix_on_a_sample_blocks_and_escalates_every_item(
    client: TestClient, world: World, sender: Any, tpl_root: Path, tmode: None
) -> None:
    _, outside = _invite(client, world, sender, "outside@example.com")
    _approve_samples(client, world.teacher_token, T_SAMPLES)
    digest = _cards(client, outside, "all")["ITEM.T4"]["content_hash"]
    assert _post(client, outside, _fix(digest), "ITEM.T4").status_code == 200
    state = _state(client, world, MATHS[0])
    assert state["state"] == "escalated" and state["approvals"] == 1
    assert any(r["blocking"] for r in state["reviewers"])
    todo = set(_cards(client, world.teacher_token))
    assert {"ITEM.T2", "ITEM.T3", "ITEM.T5"} <= todo  # escalated items
    assert not set(T_SAMPLES) & todo  # the teacher already decided the samples
    summary = client.get(SUMMARY, headers=auth_header(world.admin_token)).json()
    assert summary["totals"]["escalated"] == 1 and summary["totals"]["ready"] == 0
    [flagged] = summary["blocked"]
    assert flagged["template_id"] == "TPL.C10.X" and flagged["samples"] == list(T_SAMPLES)
    # the reviewer who raised the fix also owes the other items
    assert {"ITEM.T1", "ITEM.T2"} <= set(_cards(client, outside))


def test_a_small_template_with_a_block_is_blocked_not_escalated(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    digest = _cards(client, world.teacher_token, "all")["ITEM.S1"]["content_hash"]
    assert _post(client, world.teacher_token, _fix(digest), "ITEM.S1").status_code == 200
    assert _state(client, world, SMALL[0])["state"] == "blocked"


def test_changing_the_template_makes_a_new_version_and_resets(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    digest = _cards(client, world.teacher_token, "all")["ITEM.T4"]["content_hash"]
    assert _post(client, world.teacher_token, _fix(digest), "ITEM.T4").status_code == 200
    assert _state(client, world, MATHS[0])["state"] == "escalated"
    _write_maths(tpl_root, (MATHS[0], "hash-x2", MATHS[2]), "Regenerated stem")
    service.clear_items_cache()
    version = _state(client, world, MATHS[0])
    assert version["template_hash"] == "hash-x2" and version["state"] == "in_review"
    todo = set(_cards(client, world.teacher_token))
    assert {"ITEM.T2", "ITEM.T3", "ITEM.T5"}.isdisjoint(todo)
    _write_maths(
        tpl_root, (MATHS[0], "hash-x2", "factory-3"), "Regenerated stem"
    )  # a new generator is a new version
    service.clear_items_cache()
    assert _state(client, world, MATHS[0])["generator_version"] == "factory-3"


# ---- blind ----


def test_a_reviewer_learns_nothing_about_others_from_template_mode(
    client: TestClient, world: World, sender: Any, tpl_root: Path, tmode: None
) -> None:
    _, outside = _invite(client, world, sender, "outside@example.com")
    before_cards = _cards(client, world.teacher_token, "all")
    before_groups = client.get(CHAPTERS, headers=auth_header(world.teacher_token)).json()
    _approve_samples(client, outside, (*T_SAMPLES, "ITEM.S1", "ITEM.S2"))
    assert _cards(client, world.teacher_token, "all") == before_cards
    assert client.get(CHAPTERS, headers=auth_header(world.teacher_token)).json() == before_groups
    for token in (world.teacher_token, outside):  # the template routes are admin only
        assert client.get(SUMMARY, headers=auth_header(token)).status_code == 403
    summary = client.get(SUMMARY, headers=auth_header(world.admin_token)).json()
    assert summary["totals"]["ready"] == 2 and summary["totals"]["in_review"] == 1
    assert "outside@example.com" not in str(summary)
    chapter = next(c for c in summary["chapters"] if c["chapter"] == "ov1")
    assert chapter["ready"] == 2 and chapter["total"] == 3
    detail = _state(client, world, MATHS[0])
    assert detail["reviewers"][0]["label"].startswith("R-")
    assert "outside@example.com" not in str(detail)


def test_unknown_template_is_404_and_anonymous_is_401(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    out = client.get("/staff/review/templates/TPL.NOPE", headers=auth_header(world.admin_token))
    assert out.status_code == 404
    assert client.get(SUMMARY).status_code == 401


# ---- approvals are tied to the template version key ----


def _version_key(tpl: tuple[str, str, str]) -> str:
    return hashlib.sha256("|".join(tpl).encode()).hexdigest()


def test_a_template_hash_change_with_identical_text_resets_approval(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    token = world.teacher_token
    _approve_samples(client, token, T_SAMPLES)
    assert _state(client, world, MATHS[0])["state"] == "ready"
    _write_maths(tpl_root, (MATHS[0], "hash-x2", MATHS[2]))  # same question text, new template
    service.clear_items_cache()
    version = _state(client, world, MATHS[0])
    assert version["template_hash"] == "hash-x2"
    assert version["state"] == "in_review" and version["approvals"] == 0
    # the samples are owed again, and a fresh approval on the new version counts
    assert set(T_SAMPLES) <= set(_cards(client, token))
    _approve_samples(client, token, T_SAMPLES)
    assert _state(client, world, MATHS[0])["state"] == "ready"


def test_a_generator_version_change_with_identical_text_resets_approval(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    _approve_samples(client, world.teacher_token, T_SAMPLES)
    _write_maths(tpl_root, (MATHS[0], MATHS[1], "factory-3"))
    service.clear_items_cache()
    version = _state(client, world, MATHS[0])
    assert version["generator_version"] == "factory-3" and version["approvals"] == 0


def test_an_old_version_block_does_not_block_the_new_version(
    client: TestClient, world: World, tpl_root: Path, tmode: None
) -> None:
    digest = _cards(client, world.teacher_token, "all")["ITEM.T4"]["content_hash"]
    assert _post(client, world.teacher_token, _fix(digest), "ITEM.T4").status_code == 200
    assert _state(client, world, MATHS[0])["state"] == "escalated"
    _write_maths(tpl_root, (MATHS[0], "hash-x2", MATHS[2]))
    service.clear_items_cache()
    assert _state(client, world, MATHS[0])["state"] == "in_review"


def test_rows_without_a_key_do_not_count_toward_template_approval(
    client: TestClient, world: World, tpl_root: Path, tmode: None, db: Any
) -> None:
    from datetime import UTC, datetime

    from app.db.models import ContentReviewRow

    cards = _cards(client, world.teacher_token, "all")
    for item_id in T_SAMPLES:
        db.add(
            ContentReviewRow(
                id=uuid.uuid4(),
                item_id=item_id,
                content_hash=cards[item_id]["content_hash"],
                reviewer_id=uuid.uuid4(),
                reviewer_label="old",
                decision="approve",
                created_at=datetime.now(UTC),
                template_key=None,
            )
        )
    db.commit()
    assert _state(client, world, MATHS[0])["approvals"] == 0
    # they still count as ordinary item decisions
    assert _cards(client, world.teacher_token, "all")["ITEM.T4"]["approvals"] is None  # blind


def test_the_key_is_stored_server_side_and_a_client_value_is_refused(
    client: TestClient, world: World, tpl_root: Path, tmode: None, db: Any
) -> None:
    from sqlalchemy import select

    from app.db.models import ContentReviewRow

    digest = _cards(client, world.teacher_token, "all")["ITEM.T4"]["content_hash"]
    forged = _approve(digest, template_key="f" * 64)
    assert _post(client, world.teacher_token, forged, "ITEM.T4").status_code == 422
    assert _post(client, world.teacher_token, _approve(digest), "ITEM.T4").status_code == 200
    plain = _cards(client, world.teacher_token, "all")["ITEM.P0"]["content_hash"]
    assert _post(client, world.teacher_token, _approve(plain), "ITEM.P0").status_code == 200
    db.expire_all()
    rows = {r.item_id: r.template_key for r in db.scalars(select(ContentReviewRow))}
    assert rows["ITEM.T4"] == _version_key(MATHS)
    assert rows["ITEM.P0"] is None


def test_flag_off_still_stores_the_key_and_blocks_at_item_level(
    client: TestClient, world: World, tpl_root: Path, desk: None
) -> None:
    digest = _cards(client, world.teacher_token, "all")["ITEM.T4"]["content_hash"]
    assert _post(client, world.teacher_token, _fix(digest), "ITEM.T4").status_code == 200
    _write_maths(tpl_root, (MATHS[0], "hash-x2", MATHS[2]))  # text unchanged: same item hash
    service.clear_items_cache()
    card = _cards(client, world.teacher_token, "all")["ITEM.T4"]
    assert card["blocked"] is True  # item-level behaviour is exactly as before
