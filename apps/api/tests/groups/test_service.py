"""Group lessons, the privacy rules: what may be sent back, and what the organiser may see."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.groups.service import (
    MAX_ITEMS,
    MIN_CELL,
    MIN_PARTICIPANTS,
    accept_items,
    new_code,
    norm,
    participant_key,
    questions_of,
    summarise,
)

PREDICT = "A ball lacks the energy to climb a hill. What happens?"
CHECK = "What happens to the chance if the barrier gets thicker?"


def blocks() -> list[dict[str, Any]]:
    return [
        {"kind": "hook", "text": "t", "question": "q"},
        {
            "kind": "predict",
            "prompt": PREDICT,
            "free_text": False,
            "options": ["It rolls back", "It appears on the other side"],
            "correct": 0,
            "reveal_after": "r",
            "misconceptions": [None, "thinks a ball can pass through the hill"],
        },
        {"kind": "predict", "prompt": "Say it in your words", "free_text": True, "correct": None},
        {
            "kind": "check",
            "question": CHECK,
            "options": ["a", "b", "c", "d"],
            "correct": 1,
            "misconceptions": ["thinks thicker helps", None, "thinks width is irrelevant", "x"],
        },
        {"kind": "recap", "three_bullets": ["a", "b", "c"]},
    ]


def item(
    question: str, right: bool, confidence: str | None = None, idea: str | None = None
) -> dict:
    kind = "predict" if question == PREDICT else "check"
    return {
        "question": question,
        "kind": kind,
        "right": right,
        "confidence": confidence,
        "idea": idea,
    }


# ── identity ─────────────────────────────────────────────────────────────────


def test_a_participant_key_is_stable_per_group_and_differs_across_groups_and_people() -> None:
    group, other_group = uuid.uuid4(), uuid.uuid4()
    student, other_student = uuid.uuid4(), uuid.uuid4()
    first = participant_key("pepper", group, student)
    assert first == participant_key("pepper", group, student)
    assert first != participant_key("pepper", other_group, student)  # not followed across groups
    assert first != participant_key("pepper", group, other_student)
    assert first != participant_key("other pepper", group, student)  # depends on the secret
    assert len(first) == 64 and str(student) not in first and str(group) not in first


def test_codes_are_short_url_safe_and_do_not_repeat() -> None:
    codes = {new_code() for _ in range(200)}
    assert len(codes) == 200
    assert all(6 <= len(c) <= 16 and all(ch.isalnum() or ch in "-_" for ch in c) for c in codes)


# ── what may be sent ─────────────────────────────────────────────────────────


def test_only_judged_questions_count_and_free_text_is_left_out() -> None:
    known = questions_of(blocks())
    assert set(known) == {norm(PREDICT), norm(CHECK)}
    assert known[norm(PREDICT)]["kind"] == "predict"
    assert known[norm(CHECK)]["ideas"] == {
        norm("thinks thicker helps"): "thinks thicker helps",
        norm("thinks width is irrelevant"): "thinks width is irrelevant",
        norm("x"): "x",
    }


def test_the_page_is_not_trusted_about_the_questions_the_kind_or_the_ideas() -> None:
    sent = [
        item(PREDICT, False, "sure", "thinks a ball can pass through the hill"),
        item("A question the lesson never asked", False, "sure", "anything"),
        {**item(CHECK, True), "kind": "predict"},  # the wrong kind for that question
        item(CHECK, False, "unsure", "an idea the lesson never named"),
    ]
    accepted = accept_items(blocks(), sent)
    # the invented question and the wrong-kind answer are dropped; the real check stays,
    # without the invented idea
    assert [a["question"] for a in accepted] == [PREDICT, CHECK]
    assert accepted[0]["idea"] == "thinks a ball can pass through the hill"
    assert accepted[1]["idea"] is None


def test_an_unknown_idea_is_dropped_but_the_answer_is_kept() -> None:
    accepted = accept_items(blocks(), [item(CHECK, False, "sure", "something invented")])
    assert accepted == [
        {"question": CHECK, "kind": "check", "right": False, "confidence": "sure", "idea": None}
    ]


def test_a_right_answer_never_carries_an_idea_and_odd_confidence_is_dropped() -> None:
    accepted = accept_items(
        blocks(), [item(PREDICT, True, "very sure", "thinks a ball can pass through the hill")]
    )
    assert accepted[0]["idea"] is None and accepted[0]["confidence"] is None


def test_the_same_question_counts_once_and_the_list_is_capped() -> None:
    twice = accept_items(blocks(), [item(PREDICT, True), item(PREDICT, False)])
    assert len(twice) == 1 and twice[0]["right"] is True
    many = [item(PREDICT, True)] * (MAX_ITEMS * 3)
    assert len(accept_items(blocks(), many)) == 1


def test_matching_ignores_spacing_and_case() -> None:
    sloppy = {
        **item(PREDICT, True),
        "question": "  a BALL lacks the   energy to climb a hill. What happens? ",
    }
    assert accept_items(blocks(), [sloppy])[0]["question"] == PREDICT


# ── what the organiser may see ───────────────────────────────────────────────


def people(
    n: int, wrong: int, sure_wrong: int, idea: str = "thinks thicker helps"
) -> list[list[dict]]:
    """n people who answered the check: the first `wrong` were wrong, `sure_wrong` of those sure."""
    out = []
    for i in range(n):
        if i < wrong:
            out.append([item(CHECK, False, "sure" if i < sure_wrong else "unsure", idea)])
        else:
            out.append([item(CHECK, True, "sure")])
    return out


def test_nothing_is_shown_until_enough_people_have_sent_results() -> None:
    for n in range(MIN_PARTICIPANTS):
        shown = summarise(blocks(), people(n, wrong=n, sure_wrong=n))
        assert shown["ready"] is False and shown["questions"] == [] and shown["participants"] == n


def test_once_there_are_enough_people_each_question_is_summarised() -> None:
    shown = summarise(blocks(), people(8, wrong=5, sure_wrong=4))
    assert shown["ready"] is True and shown["minimum"] == MIN_PARTICIPANTS
    (row,) = shown["questions"]
    assert row["question"] == CHECK
    assert (row["answered"], row["wrong"], row["sure_wrong"]) == (8, 5, 4)
    assert row["ideas"] == [{"idea": "thinks thicker helps", "count": 5}]


def test_a_count_small_enough_to_point_at_someone_is_hidden() -> None:
    shown = summarise(blocks(), people(8, wrong=MIN_CELL - 1, sure_wrong=MIN_CELL - 1))
    (row,) = shown["questions"]
    assert row["wrong"] is None and row["sure_wrong"] is None and row["ideas"] == []


def test_a_small_confident_error_count_is_hidden_even_when_the_total_is_shown() -> None:
    shown = summarise(blocks(), people(9, wrong=6, sure_wrong=MIN_CELL - 1))
    (row,) = shown["questions"]
    assert row["wrong"] == 6 and row["sure_wrong"] is None


def test_the_number_who_got_it_right_is_never_given_so_a_hidden_count_cannot_be_subtracted() -> (
    None
):
    shown = summarise(blocks(), people(7, wrong=1, sure_wrong=1))
    (row,) = shown["questions"]
    assert row["wrong"] is None
    assert set(row) == {"question", "kind", "answered", "wrong", "sure_wrong", "ideas"}


def test_ideas_are_listed_by_how_many_share_them_and_only_when_enough_do() -> None:
    mixed = people(6, wrong=0, sure_wrong=0)
    for i in range(4):
        mixed[i] = [item(CHECK, False, "unsure", "thinks thicker helps")]
    mixed[4] = [item(CHECK, False, "unsure", "thinks width is irrelevant")]
    (row,) = summarise(blocks(), mixed)["questions"]
    assert row["ideas"] == [
        {"idea": "thinks thicker helps", "count": 4}
    ]  # the idea one person had is hidden


def test_a_question_few_people_answered_is_left_out() -> None:
    results = people(6, wrong=3, sure_wrong=0)
    for person in results[: 6 - (MIN_PARTICIPANTS - 1)]:
        person.clear()  # only four answered this question
    assert summarise(blocks(), results)["questions"] == []


@pytest.mark.parametrize("n", [MIN_PARTICIPANTS, MIN_PARTICIPANTS + 1])
def test_the_edge_of_the_minimum_is_exact(n: int) -> None:
    assert summarise(blocks(), people(n, wrong=n, sure_wrong=0))["ready"] is True
    assert (
        summarise(blocks(), people(MIN_PARTICIPANTS - 1, wrong=0, sure_wrong=0))["ready"] is False
    )
