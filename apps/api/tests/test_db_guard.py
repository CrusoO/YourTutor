"""The suite drops every table in TEST_DATABASE_URL; it must refuse a non-test database."""

from __future__ import annotations

import pytest

from tests.db_guard import UnsafeTestDatabase, assert_safe_test_database


@pytest.mark.parametrize(
    "url",
    [
        "sqlite://",
        "sqlite:///:memory:",
        "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_test",
        "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_test2",
        "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_test_b",
    ],
)
def test_a_test_database_is_allowed(url: str) -> None:
    assert_safe_test_database(url, environ={})


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor",
        "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_preview",
        "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/postgres",
        "postgresql+psycopg://u:p@db.example.neon.tech/neondb?sslmode=require",
    ],
)
def test_any_other_database_is_refused_with_the_name_in_the_message(url: str) -> None:
    with pytest.raises(UnsafeTestDatabase) as info:
        assert_safe_test_database(url, environ={})
    message = str(info.value)
    assert "tutor:tutor" not in message and ":p@" not in message  # no password in the message


def test_a_disposable_ci_database_is_allowed_when_ci_says_so() -> None:
    url = "postgresql+psycopg://tutor:tutor@localhost:5432/yourtutor"
    assert_safe_test_database(url, environ={"CI": "true"})


def test_an_explicit_opt_in_allows_it_and_nothing_else_does() -> None:
    url = "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_preview"
    assert_safe_test_database(url, environ={"ALLOW_TEST_DATABASE_WIPE": "yourtutor_preview"})
    with pytest.raises(UnsafeTestDatabase):
        assert_safe_test_database(url, environ={"ALLOW_TEST_DATABASE_WIPE": "yourtutor"})
    with pytest.raises(UnsafeTestDatabase):
        assert_safe_test_database(url, environ={"ALLOW_TEST_DATABASE_WIPE": "1"})


def test_an_unreadable_url_is_refused() -> None:
    with pytest.raises(UnsafeTestDatabase):
        assert_safe_test_database("not a url", environ={})
