"""Plain-language rules for hints, step explanations and misconception messages."""

from __future__ import annotations

from app.content.plain_language import (
    PlainReport,
    default_rules,
    format_counts,
    grade_level,
    lint_bundle_plain,
    lint_item_plain,
    lint_misconception_message,
    lint_reading,
    misconception_mismatches,
    unexplained_jargon,
)
from app.content.schema import Item, Misconception, Skill
from tests.content.conftest import minimal_item

RULES = default_rules()


def _rules_of(findings: list) -> set[str]:
    return {f.rule for f in findings}


def _mc(mc_id: str, text: str) -> Misconception:
    return Misconception.model_validate(
        {
            "id": mc_id,
            "title": {"en": "t"},
            "explanation": {"en": text},
            "remedial_skill": "S.ONE",
        }
    )


def _skill(skill_id: str, mcs: list[str]) -> Skill:
    return Skill.model_validate(
        {
            "id": skill_id,
            "title": {"en": "t"},
            "grade_band": [7],
            "subject": "math",
            "misconceptions": mcs,
            "bkt": {"p_init": 0.2, "p_learn": 0.1, "p_slip": 0.1, "p_guess": 0.2},
        }
    )


def _mcq(rules: list[dict], hints: list[str], skill: str = "S.ONE") -> Item:
    data = minimal_item("ITEM.PL.1", stem="Which is 10 + (-7)?", answer="a")
    data["skill_ids"] = [skill]
    data["type"] = "mcq"
    data["options"] = [{"id": "a", "en": "3"}, {"id": "b", "en": "17"}, {"id": "c", "en": "-3"}]
    data["answer"] = {"sympy": "a", "accept": []}
    data["solution_steps"] = [{"en": "Take 7 away from 10."}, {"en": "You get 3."}]
    padded = [*hints, "Try again.", "Try once more.", "Last try."][:3]
    data["hints"] = [{"level": i + 1, "en": h} for i, h in enumerate(padded)]
    data["misconception_rules"] = rules
    return Item.model_validate(data)


def test_the_thresholds_come_from_config() -> None:
    assert RULES.max_sentence_words == 12
    assert "inverse" in RULES.jargon and "coefficient" in RULES.jargon


def test_a_long_sentence_is_a_warning() -> None:
    long = "Take the number you were given and keep going until you have used every one of them."
    assert "PL.SENTENCE_LONG" in _rules_of(lint_reading(long, "X", RULES))
    assert not lint_reading("Take 7 away from 10.", "X", RULES)


def test_formulas_do_not_count_as_words() -> None:
    assert not lint_reading("Use a_n = a + (n - 1) * d = 4 + 3 * 5 = 19 now.", "X", RULES)


def test_hard_reading_level_is_a_warning() -> None:
    hard = (
        "Notwithstanding the aforementioned considerations, systematically "
        "reconsider mathematical relationships characterising proportionality, "
        "fundamentally understanding multiplicative transformations, unquestionably."
    )
    assert (grade_level(hard) or 0) > RULES.max_grade_level
    assert "PL.READING_LEVEL" in _rules_of(lint_reading(hard, "X", RULES))


def test_jargon_must_be_explained_or_avoided() -> None:
    assert unexplained_jargon("Use the inverse operation.", RULES) == ["inverse"]
    assert not unexplained_jargon("The inverse (the opposite move) undoes it.", RULES)
    assert not unexplained_jargon("An integer means a whole number, like -3 or 5.", RULES)
    assert not unexplained_jargon("Add the numbers.", RULES)
    assert unexplained_jargon("The coefficient decides it.", RULES) == ["coefficient"]


def test_a_misconception_message_must_say_what_the_learner_did() -> None:
    rule = "The inverse of subtraction is addition, and the inverse of addition is subtraction."
    rules = _rules_of(lint_misconception_message(_mc("MC.A", rule), RULES))
    assert {"PL.MC_NOT_EVERYDAY", "PL.JARGON"} <= rules
    good = _mc("MC.B", "You may have added the numbers instead of taking one away.")
    assert not lint_misconception_message(good, RULES)


def test_a_hint_that_states_the_answer_is_an_error() -> None:
    item = _mcq([], ["Think about it.", "Start at 10 and end at 3.", "The answer is 3."])
    findings = lint_item_plain(item, RULES)
    errors = [f for f in findings if f.is_error]
    assert [f.detail for f in errors] == ["hint level 2", "hint level 3"]
    clean = _mcq([], ["Think about it.", "Take 7 away from 10.", "Count back."])
    assert not [f for f in lint_item_plain(clean, RULES) if f.is_error]


def test_a_misconception_outside_the_skills_own_list_is_an_error() -> None:
    skills = [_skill("S.ONE", ["MC.OWN"])]
    own = _mcq([{"id": "MC.OWN", "when_answer_equals": ["b"]}], ["Hint.", "Two.", "Three."])
    stray = _mcq([{"id": "MC.INVERSE", "when_answer_equals": ["b"]}], ["Hint.", "Two.", "Three."])
    assert not misconception_mismatches([own], skills)
    found = misconception_mismatches([stray], skills)
    assert [(f.rule, f.text) for f in found] == [("PL.MC_NOT_OWN", "MC.INVERSE")]


def test_the_bundle_report_counts_by_rule() -> None:
    skills = [_skill("S.ONE", ["MC.OWN"])]
    item = _mcq(
        [{"id": "MC.STRAY", "when_answer_equals": ["b"]}], ["Hint.", "Hint two.", "Hint three."]
    )
    report = lint_bundle_plain([item], skills, [_mc("MC.OWN", "The student adds.")])
    assert isinstance(report, PlainReport)
    assert report.counts() == {"PL.MC_NOT_EVERYDAY": 1, "PL.MC_NOT_OWN": 1}
    assert len(report.errors) == 1 and len(report.warnings) == 1
    assert "PL.MC_NOT_OWN: 1 (error)" in format_counts(report)
