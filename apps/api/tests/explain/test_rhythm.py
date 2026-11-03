"""The rhythm checks: what makes a story sound like a teacher thinking with the viewer."""

from __future__ import annotations

from typing import Any

import pytest

from app.explain.rhythm import (
    MAX_WORDS,
    MAX_WORDS_LONG_CHAIN,
    MIN_WORDS,
    is_question,
    rhythm_issues,
    spoken,
    total_words,
    word_count,
)

CHAIN = [
    "Water is split, giving oxygen, hydrogen ions and electrons",
    "The energy is stored in ATP and NADPH",
    "The Calvin cycle uses ATP and NADPH to turn carbon dioxide into sugar",
]


def words(n: int) -> str:
    return " ".join(["word"] * n)


def scene(*sentences: str, role: str = "build", covers: list[int] | None = None) -> dict[str, Any]:
    return {"role": role, "sentences": list(sentences), "covers": covers or []}


def good_story() -> list[dict[str, Any]]:
    """A story that follows every rule: about 190 words, four scenes, all three steps covered."""
    return [
        scene(
            "A leaf sits in the sun and makes sugar from water and air.",
            "How?",
            "Think about what the leaf is actually given: light, water, and a gas called "
            "carbon dioxide "
            "from the air, and that is all.",
            "So where does the sugar come from? [pause]",
            role="hook",
        ),
        scene(
            "First the water is split, and that releases oxygen, hydrogen ions and electrons "
            "into the leaf "
            "while the light does the work of pulling it apart.",
            "Splitting water.",
            "Where does the hydrogen go?",
            "It does not just sit there.",
            role="build",
            covers=[1],
        ),
        scene(
            "The energy of the light is captured and stored in two small carriers, "
            "ATP and NADPH, which "
            "hold both the energy and the hydrogen ready to use.",
            "So what are they for?",
            "Think of them as charged batteries.",
            role="build",
            covers=[2],
        ),
        scene(
            "Now the Calvin cycle uses the energy in ATP and the hydrogen in NADPH to turn "
            "carbon dioxide "
            "from the air into sugar, step by step, inside the leaf.",
            "That is the sugar.",
            "The sugar was built from air and water, powered by light. [slow]",
            role="reveal",
            covers=[3],
        ),
    ]


def test_a_well_built_story_has_no_issues() -> None:
    story = good_story()
    assert MIN_WORDS <= total_words(story) <= MAX_WORDS
    assert rhythm_issues(story, CHAIN) == []


# ── the building blocks ──────────────────────────────────────────────────────


def test_a_pacing_marker_is_not_a_spoken_word() -> None:
    assert spoken("Why? [pause]") == "Why?"
    assert word_count("So where does it go? [pause]") == 5
    assert word_count("It's here [slow]") == 2  # a contraction is one word
    assert is_question("Why? [pause]") and not is_question("Because. [slow]")


# ── length ───────────────────────────────────────────────────────────────────


def test_a_story_that_runs_past_two_minutes_is_told_how_far_over() -> None:
    long = good_story()
    long[1]["sentences"].append(words(MAX_WORDS))
    issues = rhythm_issues(long, CHAIN)
    assert any("at most" in i and str(MAX_WORDS) in i for i in issues)


def test_a_mechanism_with_many_steps_gets_a_little_more_room() -> None:
    many = [f"Step {n} of the process happens here in the leaf" for n in range(1, 6)]
    story = good_story()
    story[1]["sentences"].append(
        words(MAX_WORDS - total_words(story) + 20)
    )  # just over the normal ceiling
    assert any("at most" in i for i in rhythm_issues(story, CHAIN))
    assert not any("at most" in i for i in rhythm_issues(story, many))
    assert MAX_WORDS_LONG_CHAIN > MAX_WORDS


def test_a_story_under_a_minute_is_told_it_is_too_short() -> None:
    short = [
        scene("Why? [pause]", "Because.", "Really.", role="hook"),
        scene("Yes.", "No.", "Okay.", role="reveal"),
    ]
    assert any("only" in i and "at least" in i for i in rhythm_issues(short))


# ── questions ────────────────────────────────────────────────────────────────


def test_every_scene_but_the_last_must_ask_a_real_question() -> None:
    story = good_story()
    story[1]["sentences"] = [s for s in story[1]["sentences"] if not is_question(s)] + [
        "It keeps going on."
    ]
    issues = rhythm_issues(story, CHAIN)
    assert any(i.startswith("Scene 2") and "question" in i for i in issues)
    assert not any(
        i.startswith("Scene 4") and "question" in i for i in issues
    )  # the last may land the point


# ── rhythm ───────────────────────────────────────────────────────────────────


def test_a_scene_of_same_sized_sentences_is_told_to_vary_them() -> None:
    drone = good_story()
    drone[2]["sentences"] = [
        f"{words(9)} number {n}?" if n == 0 else words(9 + n % 2) for n in range(4)
    ]
    issues = rhythm_issues(drone, CHAIN)
    assert any(
        i.startswith("Scene 3") and ("short sentence" in i or "almost the same length" in i)
        for i in issues
    )


def test_a_scene_with_no_short_or_no_long_sentence_is_told_which() -> None:
    no_short = good_story()
    no_short[2]["sentences"] = [words(8) + "?", words(15), words(11)]
    assert any(
        "short sentence" in i for i in rhythm_issues(no_short, CHAIN) if i.startswith("Scene 3")
    )
    no_long = good_story()
    no_long[2]["sentences"] = [words(3) + "?", words(5), words(9)]
    assert any("longer" in i for i in rhythm_issues(no_long, CHAIN) if i.startswith("Scene 3"))


def test_a_two_sentence_scene_is_not_held_to_the_variety_rules() -> None:
    story = good_story()
    story[2]["sentences"] = [
        "What are they for?",
        "They hold the energy and the hydrogen ready to use now.",
    ]
    assert not any(
        i.startswith("Scene 3") and ("short" in i or "longer" in i)
        for i in rhythm_issues(story, CHAIN)
    )


# ── pauses ───────────────────────────────────────────────────────────────────


def test_the_hook_needs_a_pause_and_the_reveal_a_slow_sentence() -> None:
    story = good_story()
    story[0]["sentences"] = [spoken(s) for s in story[0]["sentences"]]
    story[3]["sentences"] = [spoken(s) for s in story[3]["sentences"]]
    issues = rhythm_issues(story, CHAIN)
    assert any("[pause]" in i and i.startswith("Scene 1") for i in issues)
    assert any("[slow]" in i for i in issues)


# ── no skipped step ──────────────────────────────────────────────────────────


def test_a_step_no_scene_claims_to_cover_is_named() -> None:
    story = good_story()
    story[2]["covers"] = []  # nobody covers "ATP and NADPH"
    issues = rhythm_issues(story, CHAIN)
    assert any("Step 2" in i and "never covered" in i and "ATP and NADPH" in i for i in issues)


def test_a_scene_that_claims_a_step_it_never_says_is_caught() -> None:
    story = good_story()
    story[2]["sentences"] = [
        "Now something happens in the leaf that is hard to describe in a few words.",
        "What is it for?",
        "Nobody knows.",
    ]
    issues = rhythm_issues(story, CHAIN)
    assert any("covers step 2" in i and "never says it" in i for i in issues)


def test_a_step_number_outside_the_chain_is_ignored_not_trusted() -> None:
    story = good_story()
    story[1]["covers"] = [1, 99, "two", None]  # type: ignore[list-item]
    assert not any("Step 1" in i for i in rhythm_issues(story, CHAIN))


def test_with_no_chain_the_step_checks_are_skipped() -> None:
    story = good_story()
    for s in story:
        s["covers"] = []
    assert rhythm_issues(story, None) == []
    assert rhythm_issues(story, []) == []


@pytest.mark.parametrize("junk", [None, [], "x", 5, {}])
def test_odd_input_never_crashes(junk: Any) -> None:
    story = [{"role": "hook", "sentences": junk, "covers": junk}]
    assert isinstance(rhythm_issues(story, CHAIN), list)
