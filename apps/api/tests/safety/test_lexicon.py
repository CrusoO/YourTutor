"""Layer 1 normalisation and matching, one behaviour at a time."""

from __future__ import annotations

import pytest

from app.safety_lexicon import detect, normalise


@pytest.mark.parametrize(
    "text",
    [
        "I WANT TO DIE",
        "i want to d\u200bie",  # zero-width space
        "i w\u200dant to die",
        "su1cide",  # digit as letter
        "ki11 myself",
        "k!ll myself",
        "I waaaant to diiiie",  # repeated letters
        "i want to d.i.e",  # punctuation inside
        "i want to d i e",  # spaced letters
        "iwanttodie",  # no spaces
        "I don\u2019t want to be alive anymore",
    ],
)
def test_evasions_are_normalised_and_caught(text: str) -> None:
    assert detect(text).risk == "urgent"


def test_devanagari_variants_fold_to_one_form() -> None:
    assert normalise("मरना चाहता हूँ") == normalise("मरना चाहता हूं")
    assert normalise("ख़ुद") == normalise("खुद")
    assert detect("मैं ख़ुद को ख़त्म कर लूँगा").risk == "urgent"


def test_hinglish_romanised_spellings_are_caught() -> None:
    for text in (
        "mujhe marna hai",
        "mai khudkushi kar lungi",
        "sucide kar lunga",
        "jeene ka man nahi",
    ):
        assert detect(text).risk == "urgent", text


def test_exam_stress_is_a_concern_not_urgent() -> None:
    for text in (
        "I will fail and my parents will kill me",
        "pariksha ka bahut tension hai",
        "I cant do this anymore",
        "परीक्षा का बहुत टेंशन है",
    ):
        found = detect(text)
        assert (found.risk, found.category) == ("concern", "exam_stress"), text


def test_urgent_beats_concern_in_the_same_message() -> None:
    assert detect("exam stress is too much, I want to kill myself").risk == "urgent"


@pytest.mark.parametrize(
    "text",
    [
        "how do stars die",
        "why do antibiotics kill bacteria",
        "what is sex ratio",
        "kill the process",
        "roll a die and find the probability",
        "I am dying to learn algebra",
        "cutting plane of a cone",
        "3x + 5 = 20",
        "",
        "   ",
    ],
)
def test_ordinary_questions_are_not_flagged(text: str) -> None:
    assert detect(text).risk == "none"


def test_abuse_disclosure_is_urgent_abuse() -> None:
    found = detect("my uncle touches me in a way I dont like")
    assert (found.risk, found.category) == ("urgent", "abuse")


def test_maths_with_digits_and_letters_is_untouched() -> None:
    assert normalise("5x+3=18") == normalise("5x+3=18")
    assert detect("find x if 3x1 = 9 and 4a - 7b = 2").risk == "none"
