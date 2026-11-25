"""One DATABASE_URL (as Neon hands it out) replaces the five POSTGRES_* parts."""

from __future__ import annotations

import pytest

from app.config import Settings, production_secret_errors, settings
from app.db.session import database_url, normalise_database_url

NEON = "postgresql://owner:s3cret@ep-example-123.ap-south-1.aws.neon.tech/neondb?sslmode=require"


@pytest.mark.parametrize(
    ("given", "wanted"),
    [
        (
            NEON,
            "postgresql+psycopg://owner:s3cret@ep-example-123.ap-south-1.aws.neon.tech/neondb?sslmode=require",
        ),
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("  postgresql://u:p@h/d  ", "postgresql+psycopg://u:p@h/d"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_a_hosts_address_is_put_in_the_form_the_driver_wants(given: str, wanted: str) -> None:
    assert normalise_database_url(given) == wanted


def test_an_explicit_address_beats_the_setting_which_beats_the_parts() -> None:
    settings.app_env = "production"
    settings.database_url = ""
    parts = database_url()
    assert parts.startswith("postgresql+psycopg://") and "@" in parts
    settings.database_url = NEON
    assert database_url().startswith("postgresql+psycopg://owner:")
    assert database_url("sqlite://") == "sqlite://"


def test_database_url_is_ignored_outside_production() -> None:
    """An old DATABASE_URL line on a laptop must not point dev, tests or migrations at a real DB."""
    settings.database_url = NEON
    for env in ("development", "test", ""):
        settings.app_env = env
        assert "neon.tech" not in database_url()


def test_production_accepts_a_database_url_instead_of_the_password_part() -> None:
    bare = Settings(app_env="production", database_url="")
    assert production_secret_errors(bare) == ["POSTGRES_PASSWORD"]
    assert production_secret_errors(Settings(app_env="production", database_url=NEON)) == []
    assert production_secret_errors(Settings(app_env="development", database_url="")) == []
