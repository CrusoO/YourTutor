import os
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app import health, main
from app.config import settings
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "api"


def test_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda url=None: True)
    monkeypatch.setattr(main, "ping_redis", lambda: "ok")
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["database"] == "ok" and body["redis"] == "ok"


def test_ready_answers_503_with_a_plain_body_when_the_database_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "check_database", lambda url=None: False)
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable" and body["database"] == "down"
    assert "allow_draft_content" not in body
    assert client.get("/health").status_code == 200  # liveness is separate and unchanged


def test_ready_does_not_fail_because_redis_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda url=None: True)
    monkeypatch.setattr(main, "ping_redis", lambda: "down")
    response = client.get("/ready")
    assert response.status_code == 200 and response.json()["redis"] == "down"


def test_a_hung_database_check_answers_503_within_the_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def hang(url: str | None = None) -> bool:
        time.sleep(1.0)
        return True

    monkeypatch.setattr(health, "DB_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(health, "check_database", hang)
    started = time.monotonic()
    assert client.get("/ready").status_code == 503
    assert time.monotonic() - started < 0.9


def test_a_database_error_never_reaches_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "password authentication failed for user tutor at 10.1.2.3"

    def boom(*args: object, **kwargs: object) -> None:
        raise OperationalError("select 1", {}, Exception(secret))

    monkeypatch.setattr(health, "create_engine", boom)
    response = client.get("/ready")
    assert response.status_code == 503
    assert "password" not in response.text and "10.1.2.3" not in response.text


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="needs a running Postgres (TEST_DATABASE_URL)",
)
def test_ready_with_the_wrong_database_password_is_503_and_the_right_one_is_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = make_url(os.environ["TEST_DATABASE_URL"])
    monkeypatch.setattr(settings, "postgres_user", url.username or "")
    monkeypatch.setattr(settings, "postgres_host", url.host or "127.0.0.1")
    monkeypatch.setattr(settings, "postgres_port", url.port or 5432)
    monkeypatch.setattr(settings, "postgres_db", url.database or "")
    monkeypatch.setattr(settings, "postgres_password", url.password or "")
    assert client.get("/ready").status_code == 200
    monkeypatch.setattr(settings, "postgres_password", "not-the-password-" + "x" * 8)
    response = client.get("/ready")
    assert response.status_code == 503
    assert "password" not in response.text and "authentication" not in response.text
