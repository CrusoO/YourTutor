from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from tests.conftest import World, auth_header


def test_pin_lockout_after_five_failures(client: TestClient, world: World) -> None:
    student_id = world.student_share_id
    for _ in range(settings.pin_max_attempts):
        response = client.post(f"/students/{student_id}/pin/verify", json={"pin": "0000"})
        assert response.status_code == 401
    locked = client.post(f"/students/{student_id}/pin/verify", json={"pin": "0000"})
    assert locked.status_code == 423
    still = client.post(f"/students/{student_id}/pin/verify", json={"pin": "1234"})
    assert still.status_code == 423


def test_teacher_cannot_set_pin(client: TestClient, world: World) -> None:
    response = client.post(
        f"/students/{world.student_share_id}/pin",
        json={"pin": "9999"},
        headers=auth_header(world.teacher_token),
    )
    assert response.status_code == 403
