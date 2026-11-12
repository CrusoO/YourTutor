"""A token must be committed before the response that carries it is sent.

FastAPI runs a yield-dependency's exit (our commit) after the response is sent. A browser that signs
in and at once calls GET /students/me/today could arrive before the row was committed: a 401.
These endpoints commit explicitly, before returning; the test calls them with a recording session.
"""

from __future__ import annotations

from typing import Any

from app.auth import router as auth_router


class _Db:
    def __init__(self) -> None:
        self.events: list[str] = []

    def commit(self) -> None:
        self.events.append("commit")


def test_student_login_commits_before_returning(monkeypatch: Any) -> None:
    db = _Db()

    def fake_verify(_db: Any, _who: str, _pin: str) -> str:
        db.events.append("issue")
        return "tok"

    monkeypatch.setattr(auth_router.service, "verify_family_pin", fake_verify)
    monkeypatch.setattr(auth_router.service, "verify_username_pin", fake_verify)
    for body in (
        auth_router.FamilyLoginIn(family_code="ABCD2345", pin="1234"),
        auth_router.FamilyLoginIn(username="mina", pin="1234"),
    ):
        db.events.clear()
        out = auth_router.student_login(body, db)  # type: ignore[arg-type]
        assert out["access_token"] == "tok"
        assert db.events == ["issue", "commit"]
