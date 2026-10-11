"""G6 steps 4-6: school mode (staff-assigned site_id), guest role matrix, class curriculum."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClassRow, StudentRow, UserRow
from tests.conftest import World, auth_header


def _admin_assign_teacher(client: TestClient, world: World, db: Session, site: str) -> None:
    teacher = db.scalars(select(UserRow).where(UserRow.role == "teacher")).one()
    res = client.put(
        f"/users/{teacher.id}/site",
        json={"site_id": site},
        headers=auth_header(world.admin_token),
    )
    assert res.status_code == 200, res.text


def _guest(client: TestClient) -> dict:
    return client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()


# ---- classes use curriculum_id --------------------------------------------------------------


def test_a_class_is_created_with_a_curriculum_id_and_the_board_alias_still_works(
    client: TestClient, world: World
) -> None:
    head = auth_header(world.teacher_token)
    new = client.post("/classes", json={"name": "9B", "curriculum_id": "bhutan"}, headers=head)
    assert new.status_code == 200, new.text
    assert new.json()["curriculum_id"] == "bhutan"
    old = client.post("/classes", json={"name": "9C", "board": "seba"}, headers=head)
    assert old.status_code == 200 and old.json()["curriculum_id"] == "seba"
    bad = client.post("/classes", json={"name": "9D", "curriculum_id": "narnia"}, headers=head)
    assert bad.status_code == 400
    missing = client.post("/classes", json={"name": "9E"}, headers=head)
    assert missing.status_code == 422
    assert not hasattr(ClassRow, "board")


# ---- site_id: staff assign it, nobody else ---------------------------------------------------


def test_only_staff_can_assign_a_site(client: TestClient, world: World) -> None:
    body = {"site_id": "site-a"}
    url = f"/students/{world.student_share_id}/site"
    for token in (world.parent_token, world.student_token, world.comparison_token):
        assert client.put(url, json=body, headers=auth_header(token)).status_code == 403
    assert client.put(url, json=body).status_code == 401
    # a teacher with no site of their own cannot assign one
    assert client.put(url, json=body, headers=auth_header(world.teacher_token)).status_code == 403
    admin = client.put(url, json=body, headers=auth_header(world.admin_token))
    assert admin.status_code == 200 and admin.json()["site_id"] == "site-a"


def test_a_teacher_assigns_only_their_own_site(
    client: TestClient, world: World, db: Session
) -> None:
    _admin_assign_teacher(client, world, db, "site-a")
    url = f"/students/{world.student_share_id}/site"
    other = client.put(url, json={"site_id": "site-b"}, headers=auth_header(world.teacher_token))
    assert other.status_code == 403
    own = client.put(url, json={"site_id": "site-a"}, headers=auth_header(world.teacher_token))
    assert own.status_code == 200, own.text
    db.expire_all()
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None and student.site_id == "site-a"


@pytest.mark.parametrize("bad", ["", "a name with spaces", "x" * 41, "a/b"])
def test_a_site_id_is_a_short_opaque_code(client: TestClient, world: World, bad: str) -> None:
    res = client.put(
        f"/students/{world.student_share_id}/site",
        json={"site_id": bad},
        headers=auth_header(world.admin_token),
    )
    assert res.status_code == 422


def test_a_guest_cannot_be_given_a_site(client: TestClient, world: World) -> None:
    guest = _guest(client)
    res = client.put(
        f"/students/{guest['student_id']}/site",
        json={"site_id": "site-a"},
        headers=auth_header(world.admin_token),
    )
    assert res.status_code == 409


def test_site_members_adds_the_students_of_the_teachers_site_to_a_class(
    client: TestClient, world: World, db: Session
) -> None:
    _admin_assign_teacher(client, world, db, "site-a")
    client.put(
        f"/students/{world.student_noshare_id}/site",
        json={"site_id": "site-a"},
        headers=auth_header(world.admin_token),
    )
    klass = client.post(
        "/classes",
        json={"name": "Site class", "curriculum_id": "bhutan"},
        headers=auth_header(world.teacher_token),
    ).json()["id"]
    res = client.post(f"/classes/{klass}/site-members", headers=auth_header(world.teacher_token))
    assert res.status_code == 200 and res.json()["added"] == 1
    # no teacher_share on that student: a member, but the teacher still cannot see progress
    view = client.get(f"/teacher/classes/{klass}/heatmap", headers=auth_header(world.teacher_token))
    assert view.status_code == 200
    assert world.student_noshare_id not in str(view.json())


def test_students_carry_no_school_surname_phone_or_address(
    client: TestClient, world: World
) -> None:
    for field in ("school", "surname", "phone", "address"):
        res = client.post(
            "/students",
            json={"display_name": "X", "grade": 9, "board": "bhutan", field: "anything"},
            headers=auth_header(world.parent_token),
        )
        assert res.status_code == 422, field
    columns = {c.name for c in StudentRow.__table__.columns}
    assert not columns & {"school", "surname", "last_name", "phone", "address"}


# ---- the guest column of the role matrix -----------------------------------------------------


def test_a_guest_cannot_do_anything_a_family_member_does(client: TestClient) -> None:
    guest = _guest(client)
    head = auth_header(guest["token"])
    sid = guest["student_id"]
    participant = {"site_id": "s", "group": "g", "consent_id": str(uuid.uuid4())}
    cases = [
        ("POST", f"/students/{sid}/consent", {"version": "v1", "scopes": ["tutoring"]}),
        ("POST", f"/students/{sid}/pin", {"pin": "1234"}),
        ("GET", "/parents/me/export", None),
        ("DELETE", "/parents/me", None),
        ("POST", "/students", {"display_name": "X", "grade": 9, "board": "bhutan"}),
        ("POST", "/classes", {"name": "x", "curriculum_id": "bhutan"}),
        ("PUT", f"/students/{sid}/site", {"site_id": "site-a"}),
        ("POST", "/study/participants", participant),
    ]
    for method, path, body in cases:
        res = client.request(method, path, json=body, headers=head)
        assert res.status_code in (403, 404, 409, 422), (method, path, res.status_code)


def test_nobody_but_the_upgrade_can_claim_a_guest(client: TestClient, world: World) -> None:
    sid = _guest(client)["student_id"]
    for token in (world.parent_token, world.teacher_token):
        res = client.post(
            f"/students/{sid}/consent",
            json={"version": "v1", "scopes": ["tutoring", "teacher_share"]},
            headers=auth_header(token),
        )
        assert res.status_code == 403
        assert client.get(f"/students/{sid}", headers=auth_header(token)).status_code == 403


def test_staff_do_not_enrol_a_guest_in_a_class(client: TestClient, world: World) -> None:
    guest = _guest(client)
    res = client.post(
        f"/classes/{world.class_id}/members",
        json={"student_id": guest["student_id"]},
        headers=auth_header(world.teacher_token),
    )
    assert res.status_code == 409  # a guest upgrades to a family first
