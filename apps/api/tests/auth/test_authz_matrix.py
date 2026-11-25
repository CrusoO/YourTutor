from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.actor import Actor
from app.auth.authz import llm_phrasing_allowed
from app.config import settings
from app.content.gate import item_is_servable
from app.content.schema import Item
from tests.conftest import World, auth_header
from tests.content.conftest import minimal_item


def _roles(world: World) -> dict[str, str | None]:
    return {
        "parent": world.parent_token,
        "student": world.student_token,
        "teacher": world.teacher_token,
        "admin": world.admin_token,
        "comparison": world.comparison_token,
    }


def _status(client: TestClient, method: str, path: str, token: str | None, json=None) -> int:
    headers = auth_header(token) if token else {}
    response = client.request(method, path, headers=headers, json=json)
    return response.status_code


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", True),
        ("student", False),
        ("teacher", True),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_request_otp(client: TestClient, world: World, role: str, allowed: bool) -> None:
    email = {
        "parent": "parent@example.com",
        "student": "student-try@example.com",
        "teacher": "teacher@example.com",
        "admin": "admin@example.com",
        "comparison": "cmp@example.com",
    }[role]
    status = _status(client, "POST", "/auth/request-otp", _roles(world)[role], {"email": email})
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", True),
        ("student", False),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_create_student(client: TestClient, world: World, role: str, allowed: bool) -> None:
    payload = {
        "display_name": f"Kid {role}",
        "grade": 9,
        "board": "bhutan",
        "parent_id": world.parent_id,
    }
    status = _status(client, "POST", "/students", _roles(world)[role], payload)
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", True),
        ("student", False),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_consent_and_pin(client: TestClient, world: World, role: str, allowed: bool) -> None:
    consent = _status(
        client,
        "POST",
        f"/students/{world.student_noshare_id}/consent",
        _roles(world)[role],
        {"version": "v2", "scopes": ["tutoring"]},
    )
    pin = _status(
        client,
        "POST",
        f"/students/{world.student_noshare_id}/pin",
        _roles(world)[role],
        {"pin": "5555"},
    )
    assert (consent == 200) is allowed, (role, consent)
    assert (pin == 200) is allowed, (role, pin)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", True),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_start_practice_or_diagnostic(
    client: TestClient, world: World, role: str, allowed: bool
) -> None:
    status = _status(
        client,
        "POST",
        "/sessions",
        _roles(world)[role],
        {"student_id": world.student_share_id, "type": "practice"},
    )
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", True),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_checkpoint_in_tutor(
    client: TestClient, world: World, role: str, allowed: bool
) -> None:
    status = _status(
        client,
        "POST",
        "/sessions",
        _roles(world)[role],
        {"student_id": world.student_share_id, "type": "checkpoint"},
    )
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", False),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_issue_checkpoint_token(
    client: TestClient, world: World, role: str, allowed: bool
) -> None:
    status = _status(
        client,
        "POST",
        "/checkpoints/cp1/tokens",
        _roles(world)[role],
        {
            "participant_id": world.comparison_participant_id,
            "form": world.comparison_form,
            "consent_id": world.consent_share_id,
        },
    )
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", False),
        ("teacher", False),
        ("admin", False),
        ("comparison", True),
    ],
)
def test_matrix_take_checkpoint_via_token(
    client: TestClient, world: World, role: str, allowed: bool
) -> None:
    status = _status(
        client,
        "GET",
        f"/checkpoints/cp1/forms/{world.comparison_form}",
        _roles(world)[role],
    )
    assert (status == 200) is allowed, (role, status)


def test_comparison_token_wrong_form_forbidden(client: TestClient, world: World) -> None:
    other = "B" if world.comparison_form == "A" else "A"
    status = _status(client, "GET", f"/checkpoints/cp1/forms/{other}", world.comparison_token)
    assert status == 403


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", True),
        ("student", True),
        ("teacher", True),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_see_progress_share_student(
    client: TestClient, world: World, role: str, allowed: bool
) -> None:
    status = _status(
        client, "GET", f"/students/{world.student_share_id}/progress", _roles(world)[role]
    )
    assert (status == 200) is allowed, (role, status)


def test_teacher_cannot_see_student_without_teacher_share(client: TestClient, world: World) -> None:
    status = _status(
        client, "GET", f"/students/{world.student_noshare_id}/progress", world.teacher_token
    )
    assert status == 403
    heat = client.get(
        f"/teacher/classes/{world.class_id}/heatmap",
        headers=auth_header(world.teacher_token),
    )
    ids = {row["id"] for row in heat.json()["students"]}
    assert world.student_share_id in ids
    assert world.student_noshare_id not in ids


def test_other_parent_cannot_see_child(client: TestClient, world: World) -> None:
    status = _status(
        client,
        "GET",
        f"/students/{world.student_share_id}/progress",
        world.other_parent_token,
    )
    assert status == 403


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", True),
        ("student", False),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_export_family(client: TestClient, world: World, role: str, allowed: bool) -> None:
    path = "/parents/me/export" if role == "parent" else f"/parents/{world.parent_id}/export"
    status = _status(client, "GET", path, _roles(world)[role])
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", False),
        ("teacher", True),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_heatmap_stuck_review(
    client: TestClient, world: World, role: str, allowed: bool
) -> None:
    heat = _status(client, "GET", f"/teacher/classes/{world.class_id}/heatmap", _roles(world)[role])
    stuck = _status(client, "GET", f"/teacher/classes/{world.class_id}/stuck", _roles(world)[role])
    queue = _status(client, "GET", "/teacher/review-queue", _roles(world)[role])
    assert (heat == 200) is allowed, (role, heat)
    assert (stuck == 200) is allowed, (role, stuck)
    assert (queue == 200) is allowed, (role, queue)


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", False),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_analytics_csv(client: TestClient, world: World, role: str, allowed: bool) -> None:
    status = _status(client, "GET", "/analytics/export", _roles(world)[role])
    assert (status == 200) is allowed, (role, status)
    if allowed:
        body = client.get("/analytics/export", headers=auth_header(world.admin_token)).json()
        rows = body["rows"]
        assert "pseudonym,group,site,form,occasion,score" in body["csv"]
        assert rows
        assert "display_name" not in rows[0]
        assert "student_id" not in rows[0]
        assert rows[0]["site"] == "site-thimphu"


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", True),
        ("teacher", False),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_llm_phrasing(world: World, role: str, allowed: bool) -> None:
    actor = Actor(
        role=role,
        user_id=uuid.UUID(world.parent_id) if role in {"parent", "admin", "teacher"} else None,
        student_id=uuid.UUID(world.student_share_id) if role == "student" else None,
    )
    scopes = {"tutoring", "ai_processing"}
    assert llm_phrasing_allowed(actor, scopes) is allowed
    assert llm_phrasing_allowed(actor, {"tutoring"}) is False


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", True),
        ("student", True),
        ("teacher", True),
        ("admin", True),
        ("comparison", False),
    ],
)
def test_matrix_load_draft_content(role: str, allowed: bool) -> None:
    previous = settings.allow_draft_content
    try:
        settings.allow_draft_content = True
        actor = Actor(role=role)
        item = Item.model_validate(minimal_item())
        assert item_is_servable(item, actor=actor) is allowed
        settings.allow_draft_content = False
        assert item_is_servable(item, actor=actor) is False
    finally:
        settings.allow_draft_content = previous


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("parent", False),
        ("student", False),
        ("teacher", True),
        ("admin", True),
        ("comparison", False),
        ("reviewer", True),
    ],
)
def test_matrix_content_review_with_the_reviewer_desk(
    client: TestClient, world: World, sender, db, role: str, allowed: bool
) -> None:
    from tests.conftest import seed_user, signup

    settings.reviewer_desk_enabled = True
    tokens = {
        **_roles(world),
        "reviewer": signup(client, sender, seed_user(db, "reviewer", "rv@example.com").email),
    }
    status = _status(client, "GET", "/staff/review/items", tokens[role])
    assert (status == 200) is allowed, (role, status)


@pytest.mark.parametrize(
    "role,chapters,pay",
    [
        ("parent", 403, 403),
        ("student", 403, 403),
        ("teacher", 200, 403),
        ("admin", 200, 200),
        ("comparison", 403, 403),
        ("reviewer", 200, 403),
    ],
)
def test_matrix_reviewer_chapters_and_pay_statement(
    client: TestClient, world: World, sender, db, role: str, chapters: int, pay: int
) -> None:
    from tests.conftest import seed_user, signup

    settings.reviewer_desk_enabled = True
    tokens = {
        **_roles(world),
        "reviewer": signup(client, sender, seed_user(db, "reviewer", "rv@example.com").email),
    }
    assert _status(client, "GET", "/staff/review/chapters", tokens[role]) == chapters
    url = "/staff/review/pay-statement?from=2026-03-01&to=2026-03-31"
    assert _status(client, "GET", url, tokens[role]) == pay
    assert _status(client, "GET", "/staff/review/chapters", None) == 401
    settings.reviewer_desk_enabled = False
    assert _status(client, "GET", "/staff/review/chapters", tokens["admin"]) == 404
    assert _status(client, "GET", url, tokens["admin"]) == 404


@pytest.mark.parametrize(
    "role,expected",
    [
        ("parent", 403),
        ("student", 403),
        ("teacher", 403),
        ("admin", 200),
        ("comparison", 403),
        ("reviewer", 403),
    ],
)
def test_matrix_reviewer_template_summary_is_admin_only(
    client: TestClient, world: World, sender, db, role: str, expected: int
) -> None:
    from tests.conftest import seed_user, signup

    settings.reviewer_desk_enabled = True
    settings.review_template_approval_enabled = True
    tokens = {
        **_roles(world),
        "reviewer": signup(client, sender, seed_user(db, "reviewer", "rv@example.com").email),
    }
    for path in ("/staff/review/templates/summary", "/staff/review/templates/TPL.ANY"):
        want = 404 if path.endswith("TPL.ANY") and expected == 200 else expected
        assert _status(client, "GET", path, tokens[role]) == want, (role, path)
    assert _status(client, "GET", "/staff/review/templates/summary", None) == 401
    settings.review_template_approval_enabled = False  # flag off: an unknown route for everyone
    assert _status(client, "GET", "/staff/review/templates/summary", tokens["admin"]) == 404
    settings.review_template_approval_enabled = True
    settings.reviewer_desk_enabled = False  # desk off: the same
    assert _status(client, "GET", "/staff/review/templates/summary", tokens["admin"]) == 404


def test_a_reviewer_reaches_nothing_but_content_review(
    client: TestClient, world: World, sender, db
) -> None:
    from tests.conftest import seed_user, signup

    settings.reviewer_desk_enabled = True
    token = signup(client, sender, seed_user(db, "reviewer", "rv@example.com").email)
    # every matrix route above, tried as a reviewer: all refused
    for method, path, body in (
        (
            "POST",
            "/students",
            {"display_name": "K", "grade": 9, "board": "bhutan", "parent_id": world.parent_id},
        ),
        (
            "POST",
            f"/students/{world.student_noshare_id}/consent",
            {"version": "v2", "scopes": ["tutoring"]},
        ),
        ("POST", f"/students/{world.student_noshare_id}/pin", {"pin": "5555"}),
        ("POST", "/sessions", {"student_id": world.student_share_id, "type": "practice"}),
        ("GET", f"/students/{world.student_share_id}/progress", None),
        ("GET", f"/parents/{world.parent_id}/export", None),
        ("GET", f"/teacher/classes/{world.class_id}/heatmap", None),
        ("GET", "/teacher/review-queue", None),
        ("GET", "/analytics/export", None),
        ("GET", f"/checkpoints/cp1/forms/{world.comparison_form}", None),
    ):
        assert _status(client, method, path, token, body) == 403, path
    assert _status(client, "GET", "/staff/review/items", token) == 200
    assert _status(client, "GET", "/staff/review/me/today", token) == 200
    assert _status(client, "GET", "/staff/review/reviewers", token) == 403  # admin only
    assert _status(client, "GET", "/staff/review/chapters", token) == 200
    settings.review_template_approval_enabled = True
    assert _status(client, "GET", "/staff/review/templates/summary", token) == 403
    assert (
        _status(client, "GET", "/staff/review/pay-statement?from=2026-03-01&to=2026-03-31", token)
        == 403
    )


@pytest.mark.parametrize(
    "role,expected",
    [
        ("anonymous", 401),
        ("parent", 403),
        ("student", 403),
        ("teacher", 403),
        ("comparison", 403),
        ("reviewer", 403),
        ("admin", 200),
    ],
)
def test_matrix_reviewer_sign_in_code_is_admin_only(
    client: TestClient, world: World, sender, db, role: str, expected: int
) -> None:
    from tests.conftest import seed_user, signup

    settings.reviewer_desk_enabled = True
    target = seed_user(db, "reviewer", "target@example.com")
    tokens = {
        **_roles(world),
        "reviewer": signup(client, sender, seed_user(db, "reviewer", "rv3@example.com").email),
        "anonymous": "",
    }
    path = f"/staff/review/reviewers/{target.id}/sign-in-code"
    assert _status(client, "POST", path, tokens[role]) == expected, role
