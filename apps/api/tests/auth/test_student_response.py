"""G5 step 3: student API responses carry curriculum_id and context_key, not the old board field."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import World, auth_header


def test_get_student_returns_context_not_board(client: TestClient, world: World) -> None:
    response = client.get(
        f"/students/{world.student_share_id}", headers=auth_header(world.student_token)
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "board" not in data
    assert data["curriculum_id"] == "bhutan" and data["grade"] == 9
    assert data["context_key"]["curriculum_id"] == "bhutan"
    assert data["home_language"] and data["timezone"]


def test_the_family_export_lists_curriculum_not_board(client: TestClient, world: World) -> None:
    export = client.get("/parents/me/export", headers=auth_header(world.parent_token))
    assert export.status_code == 200, export.text
    for student in export.json()["students"]:
        assert "board" not in student and student["curriculum_id"]
