"""G11: an unexpected error shows nothing internal, and the operator check says what is wrong."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import operator
from app.config import settings
from app.main import app


def test_an_unexpected_error_returns_a_generic_body_with_a_request_id() -> None:
    @app.get("/__boom")
    def boom() -> None:
        raise RuntimeError("secret detail: password=hunter2")

    with TestClient(app, raise_server_exceptions=False) as quiet:
        res = quiet.get("/__boom")
    assert res.status_code == 500
    body = res.json()
    assert body["detail"] == "something went wrong" and len(body["request_id"]) == 12
    assert "hunter2" not in res.text and res.headers["X-Request-Id"] == body["request_id"]


def test_the_check_reports_every_failure_and_exits_nonzero_when_the_database_is_down(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken():  # noqa: ANN202
        raise ConnectionError("no database")

    monkeypatch.setattr(operator, "session_factory", lambda: broken)
    assert operator.main(["check"]) == 1
    out = capsys.readouterr().out
    assert "FAIL database" in out and "ok   jurisdiction profile" in out


def test_production_with_draft_content_dev_tools_or_the_default_pepper_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        operator, "session_factory", lambda: lambda: (_ for _ in ()).throw(OSError())
    )
    settings.app_env = "production"
    settings.allow_draft_content = True
    settings.dev_tools = True
    settings.token_pepper = "dev-only-change-me"
    settings.postgres_password = "tutor"
    failed = {c.name for c in operator.run_checks() if not c.ok}
    assert {
        "draft content off in production",
        "dev tools off in production",
        "token pepper changed",
        "database password changed",
        "email for codes and reports",
    } <= failed


def test_a_development_install_passes_the_switch_checks() -> None:
    settings.app_env = "development"
    names = {c.name: c.ok for c in operator.run_checks()}
    assert names["draft content off in production"] and names["token pepper changed"]
    assert operator.main(["nonsense"]) == 2


def test_a_proxy_without_trusted_proxies_is_a_warning_not_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(operator, "_api_ready", lambda: {"forwarded_header_ignored": True})
    settings.trusted_proxies = ""
    check = operator._proxy_check(prod=True)
    assert check.ok and check.warning and "TRUSTED_PROXIES=127.0.0.1" in check.detail
    settings.trusted_proxies = "127.0.0.1"
    assert not operator._proxy_check(prod=True).warning
    settings.trusted_proxies = ""
    monkeypatch.setattr(operator, "_api_ready", lambda: None)  # the API is not running here
    assert not operator._proxy_check(prod=True).warning


def test_the_warning_is_printed_and_does_not_change_the_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    warned = operator.Check("proxy addresses", True, "WARN example", warning=True)
    monkeypatch.setattr(operator, "run_checks", lambda: [warned])
    assert operator.main(["check"]) == 0
    assert "warn proxy addresses: WARN example" in capsys.readouterr().out


def test_the_probe_reads_the_body_of_a_503_from_a_running_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import io
    import urllib.error

    body = io.BytesIO(b'{"status": "unavailable", "forwarded_header_ignored": true}')

    def refuse(*args: object, **kwargs: object) -> None:
        raise urllib.error.HTTPError("http://127.0.0.1/ready", 503, "unavailable", {}, body)  # type: ignore[arg-type]

    monkeypatch.setattr(operator.urllib.request, "urlopen", refuse)
    assert operator._api_ready() == {"status": "unavailable", "forwarded_header_ignored": True}
