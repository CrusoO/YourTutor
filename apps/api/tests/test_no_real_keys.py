"""No test may see a provider key from the developer's .env (one once caused a live, paid call)."""

from __future__ import annotations

from app.config import settings
from tests.conftest import PROVIDER_KEY_SETTINGS


def test_every_provider_key_is_blank_inside_a_test() -> None:
    for name in PROVIDER_KEY_SETTINGS:
        assert getattr(settings, name) == "", name


def test_the_list_covers_every_key_setting_the_app_defines() -> None:
    declared = {n for n in type(settings).model_fields if n.endswith("api_key")}
    assert declared <= set(PROVIDER_KEY_SETTINGS), declared - set(PROVIDER_KEY_SETTINGS)
