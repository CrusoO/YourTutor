"""Pure rules for class join codes: alphabet, entropy, normalising, expiry, labels."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.classes import codes

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def test_alphabet_has_no_confusable_characters_and_is_unique() -> None:
    assert not set("0O1I") & set(codes.ALPHABET)
    assert len(set(codes.ALPHABET)) == len(codes.ALPHABET) == 32


def test_generated_codes_use_the_alphabet_and_do_not_repeat() -> None:
    made = {codes.generate_code() for _ in range(500)}
    assert len(made) == 500  # 40 bits: a repeat in 500 would be a broken generator
    for code in made:
        assert len(code) == codes.CODE_LENGTH
        assert set(code) <= set(codes.ALPHABET)


def test_entropy_is_at_least_40_bits() -> None:
    import math

    assert codes.CODE_LENGTH * math.log2(len(codes.ALPHABET)) >= 40


def test_display_and_normalise_round_trip() -> None:
    code = "ABCD2345"
    assert codes.display_code(code) == "ABCD-2345"
    for typed in ("ABCD-2345", " abcd 2345 ", "abcd2345", "ABCD_2345"):
        assert codes.normalise_code(typed) == code


def test_normalise_rejects_what_cannot_be_a_code() -> None:
    for bad in ("", "ABCD", "ABCD-234", "ABCD-23456", "ABCD-O123", "ABCD-1234", "ABCD-23!5"):
        assert codes.normalise_code(bad) is None


def test_hash_is_stable_and_not_the_code() -> None:
    first = codes.code_hash("ABCD2345")
    assert first == codes.code_hash("ABCD2345")
    assert first != codes.code_hash("ABCD2346")
    assert "ABCD2345" not in first


def test_usable_means_enabled_and_not_expired() -> None:
    assert not codes.code_usable(None, None, NOW)  # disabled
    assert codes.code_usable("h", None, NOW)  # no expiry
    assert codes.code_usable("h", NOW + timedelta(seconds=1), NOW)
    assert not codes.code_usable("h", NOW, NOW)  # expires at that moment
    assert not codes.code_usable("h", NOW - timedelta(days=1), NOW)
    assert codes.is_expired(datetime(2026, 11, 10), NOW)  # naive is read as UTC


def test_only_an_adult_is_active_at_once() -> None:
    assert codes.join_status(adult=True) == "active"
    assert codes.join_status(adult=False) == "pending"
    assert codes.join_status(adult=False, guardian_shared=True) == "active"


def test_label_is_a_nickname_never_an_identifier() -> None:
    assert codes.clean_label("  Riya   K ") == "Riya K"
    for bad in (
        None,
        "",
        "   ",
        "riya@example.com",
        "call 9876543210",
        "https://x.example/me",
        "roll 20241234",
        "x" * 25,
    ):
        assert codes.clean_label(bad) is None


def test_request_labels_number_the_unlabelled_in_order() -> None:
    out = codes.request_labels([("a", None), ("b", "Ria"), ("c", None)])
    assert out == {"a": "Student 1", "b": "Ria", "c": "Student 2"}
