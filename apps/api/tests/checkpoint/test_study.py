from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.checkpoint.study import COOKIE_NAME, REFERRER_POLICY, assign_within_site
from app.db.models import CheckpointResultRow, MasteryRow, PaperEntryRow
from app.main import access_log_line
from tests.conftest import World, auth_header


def test_within_site_balances_pretest_forms() -> None:
    first, post = assign_within_site([], seed=1, group="tutor")
    assert {first, post} == {"A", "B"}
    next_form, _ = assign_within_site([first] * 3, seed=2, group="tutor")
    assert next_form != first
    cmp_first, cmp_post = assign_within_site([], seed=1, group="comparison")
    assert {cmp_first, cmp_post} == {"A", "B"}
    cmp_next, _ = assign_within_site([cmp_first] * 3, seed=2, group="comparison")
    assert cmp_next != cmp_first


def test_token_refused_without_consent(client: TestClient, world: World) -> None:
    missing = client.post(
        "/study/participants",
        json={
            "site_id": "site-x",
            "group": "comparison",
            "consent_id": str(uuid.uuid4()),
        },
        headers=auth_header(world.admin_token),
    )
    assert missing.status_code == 400
    token = client.post(
        "/checkpoints/cp1/tokens",
        json={"participant_id": str(uuid.uuid4()), "form": "A"},
        headers=auth_header(world.admin_token),
    )
    assert token.status_code in {400, 404}


def test_tutor_counterbalance_and_site_seed(client: TestClient, world: World) -> None:
    first = client.post(
        "/study/participants",
        json={
            "site_id": "site-a",
            "group": "tutor",
            "consent_id": world.consent_share_id,
            "student_id": world.student_share_id,
        },
        headers=auth_header(world.admin_token),
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["assignment_method"] == "random"
    assert body["assignment_seed"]
    assert {body["pretest_form"], body["posttest_form"]} == {"A", "B"}
    second = client.post(
        "/study/participants",
        json={
            "site_id": "site-a",
            "group": "tutor",
            "consent_id": world.consent_share_id,
            "student_id": world.student_share_id,
        },
        headers=auth_header(world.admin_token),
    )
    assert second.status_code == 200
    assert second.json()["pretest_form"] != first.json()["pretest_form"]


def test_checkpoint_submit_writes_results_not_mastery(
    client: TestClient, world: World, db
) -> None:
    before = db.query(MasteryRow).count()
    submitted = client.post(
        f"/checkpoints/cp1/forms/{world.comparison_form}/submit",
        json={"answers": [{"item_id": "ITEM.NONE", "response": "1"}], "occasion": "pretest"},
        headers=auth_header(world.comparison_token),
    )
    assert submitted.status_code == 200, submitted.text
    db.expire_all()
    assert db.query(MasteryRow).count() == before
    assert db.query(CheckpointResultRow).count() >= 1
    row = db.query(CheckpointResultRow).first()
    assert row.occasion == "pretest"
    assert row.form == world.comparison_form


def test_export_omits_students_without_research_scope(
    client: TestClient, world: World
) -> None:
    body = client.get("/analytics/export", headers=auth_header(world.admin_token)).json()
    assert "group" in body["csv"]
    assert "site" in body["csv"]
    assert "form" in body["csv"]
    assert "occasion" in body["csv"]
    assert world.student_noshare_id not in body["csv"]
    assert "display_name" not in body["csv"]
    for column in (
        "grade",
        "board",
        "diagnostic_baseline",
        "consent_version",
        "active_minutes",
        "active_days",
    ):
        assert column in body["csv"]


def test_form_order_balanced_within_site_and_arm(client: TestClient, world: World) -> None:
    tutor_forms = []
    comparison_forms = []
    for index in range(4):
        tutor = client.post(
            "/study/participants",
            json={
                "site_id": "site-balance",
                "group": "tutor",
                "consent_id": world.consent_share_id,
                "student_id": world.student_share_id,
            },
            headers=auth_header(world.admin_token),
        )
        assert tutor.status_code == 200, tutor.text
        tutor_forms.append(tutor.json()["pretest_form"])
        comparison = client.post(
            "/study/participants",
            json={
                "site_id": "site-balance",
                "group": "comparison",
                "consent_id": world.consent_share_id,
            },
            headers=auth_header(world.admin_token),
        )
        assert comparison.status_code == 200, comparison.text
        comparison_forms.append(comparison.json()["pretest_form"])
        assert {comparison.json()["pretest_form"], comparison.json()["posttest_form"]} == {"A", "B"}
    assert abs(tutor_forms.count("A") - tutor_forms.count("B")) <= 1
    assert abs(comparison_forms.count("A") - comparison_forms.count("B")) <= 1


def test_household_shares_group(client: TestClient, world: World) -> None:
    first = client.post(
        "/study/participants",
        json={
            "site_id": "site-house",
            "group": "comparison",
            "consent_id": world.consent_share_id,
            "household_id": "hh-1",
        },
        headers=auth_header(world.admin_token),
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/study/participants",
        json={
            "site_id": "site-house",
            "group": "tutor",
            "consent_id": world.consent_share_id,
            "student_id": world.student_share_id,
            "household_id": "hh-1",
        },
        headers=auth_header(world.admin_token),
    )
    assert second.status_code == 200, second.text
    assert first.json()["group"] == second.json()["group"] == "comparison"
    assert first.json()["household_id"] == second.json()["household_id"] == "hh-1"


def test_comparison_issues_pre_and_post_tokens(client: TestClient, world: World) -> None:
    extra = client.post(
        "/study/participants",
        json={
            "site_id": "site-tokens",
            "group": "comparison",
            "consent_id": world.consent_share_id,
        },
        headers=auth_header(world.admin_token),
    )
    assert extra.status_code == 200
    tokens = client.post(
        "/checkpoints/cp1/tokens",
        json={"participant_id": extra.json()["id"]},
        headers=auth_header(world.admin_token),
    )
    assert tokens.status_code == 200, tokens.text
    body = tokens.json()
    assert body["pretest"]["form"] == extra.json()["pretest_form"]
    assert body["posttest"]["form"] == extra.json()["posttest_form"]
    assert body["pretest"]["token"] != body["posttest"]["token"]


def test_cookie_exchange_and_one_submission(client: TestClient, world: World) -> None:
    extra = client.post(
        "/study/participants",
        json={
            "site_id": "site-cookie",
            "group": "comparison",
            "consent_id": world.consent_share_id,
        },
        headers=auth_header(world.admin_token),
    )
    form = extra.json()["pretest_form"]
    issued = client.post(
        "/checkpoints/cp1/tokens",
        json={"participant_id": extra.json()["id"], "form": form},
        headers=auth_header(world.admin_token),
    )
    raw = issued.json()["token"]
    first = client.get(f"/checkpoints/cp1/forms/{form}?token={raw}", follow_redirects=False)
    assert first.status_code == 302
    assert first.headers.get("referrer-policy") == REFERRER_POLICY
    assert "token=" not in first.headers.get("location", "")
    assert COOKIE_NAME in first.cookies
    loaded = client.get(f"/checkpoints/cp1/forms/{form}")
    assert loaded.status_code == 200
    assert loaded.headers.get("referrer-policy") == REFERRER_POLICY
    submitted = client.post(
        f"/checkpoints/cp1/forms/{form}/submit",
        json={"answers": [{"item_id": "ITEM.NONE", "response": "1"}], "occasion": "pretest"},
    )
    assert submitted.status_code == 200, submitted.text
    again = client.post(
        f"/checkpoints/cp1/forms/{form}/submit",
        json={"answers": [{"item_id": "ITEM.NONE", "response": "1"}], "occasion": "pretest"},
    )
    assert again.status_code == 409
    assert "token=" not in access_log_line("GET", "/checkpoints/cp1/forms/A", 302)


def test_paper_entry_mismatch_and_no_mastery(
    client: TestClient, world: World, db
) -> None:
    extra = client.post(
        "/study/participants",
        json={
            "site_id": "site-paper",
            "group": "comparison",
            "consent_id": world.consent_share_id,
        },
        headers=auth_header(world.admin_token),
    )
    pseudonym = extra.json()["pseudonym"]
    before = db.query(MasteryRow).count()
    first = client.post(
        "/admin/checkpoints/paper",
        json={
            "pseudonym": pseudonym,
            "form": extra.json()["pretest_form"],
            "occasion": "pretest",
            "entry_pass": 1,
            "answers": [{"item_id": "ITEM.NONE", "response": "1"}],
        },
        headers=auth_header(world.admin_token),
    )
    assert first.status_code == 200, first.text
    assert first.json()["mismatches"] == []
    second = client.post(
        "/admin/checkpoints/paper",
        json={
            "pseudonym": pseudonym,
            "form": extra.json()["pretest_form"],
            "occasion": "pretest",
            "entry_pass": 2,
            "answers": [{"item_id": "ITEM.NONE", "response": "9"}],
        },
        headers=auth_header(world.admin_token),
    )
    assert second.status_code == 200, second.text
    assert "ITEM.NONE" in second.json()["mismatches"]
    assert second.json()["score"] is None
    db.expire_all()
    assert db.query(MasteryRow).count() == before
    assert db.query(PaperEntryRow).count() >= 2
    screen = client.get("/admin/paper-entry", headers=auth_header(world.admin_token))
    assert screen.status_code == 200
    assert "Paper checkpoint entry" in screen.text
    forbidden = client.get("/admin/paper-entry", headers=auth_header(world.teacher_token))
    assert forbidden.status_code == 403
