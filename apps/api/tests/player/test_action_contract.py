import json
from pathlib import Path

REQUIRED_ACTION_KEYS = {"type", "can_request_hint", "can_show_solution"}


def test_session_action_fixture_matches_contract() -> None:
    root = Path(__file__).resolve().parents[4]
    fixture = root / "packages" / "shared" / "fixtures" / "session_actions" / "show_item_practice.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    missing = REQUIRED_ACTION_KEYS - set(payload)
    assert not missing, f"missing keys: {sorted(missing)}"
    assert payload["can_request_hint"] is True
    assert payload["can_show_solution"] is False
