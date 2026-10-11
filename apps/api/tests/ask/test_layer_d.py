"""G7 step 4: Layer D post-checks for answer_doubt (citations, numbers, meaning)."""

from __future__ import annotations

import pytest

from app.llm.checks import passage_texts, run_checks
from app.llm.prompt import PromptContext
from app.llm.purposes import Purpose
from app.registries.loaders import load_grade_bands

BAND = {b.id: b for b in load_grade_bands()}["upper_secondary"]  # 80 words
P1 = "PSG.LIN1.ONE_STEP.1"
P2 = "PSG.LIN1.ONE_STEP.2"
SOURCE = (
    f"[{P1}] To solve a one-step equation, do the inverse operation to both sides so the "
    "equation stays balanced. For x + 4 = 9, subtract 4 from both sides to get x = 5.\n"
    f"[{P2}] When a variable is multiplied by a number, divide both sides by that number. "
    "For 3x = 12, divide both sides by 3 to get x = 4."
)


def _ctx() -> PromptContext:
    return PromptContext(
        purpose=Purpose.answer_doubt,
        band=BAND,
        language="en",
        source=SOURCE,
        fields={"student_text": "how do I solve x + 4 = 9", "passage_ids": f"{P1},{P2}"},
    )


def test_the_passage_lines_of_the_source_are_read_back_by_id() -> None:
    assert set(passage_texts(_ctx())) == {P1, P2}


def test_a_fully_cited_answer_from_the_passages_passes() -> None:
    reply = (
        f"Do the inverse operation to both sides so the equation stays balanced. [{P1}] "
        f"For x + 4 = 9, subtract 4 from both sides to get x = 5. [{P1}]"
    )
    checked = run_checks(_ctx(), reply)
    assert checked.ok, checked.code


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        ("Do the inverse operation to both sides.", "grounding.citation"),
        (
            f"Do the inverse operation to both sides [{P1}]. Then you always win a prize.",
            "grounding.sentence",
        ),
        (f"Subtract 4 from both sides. [{P1}] It is a trick question.", "grounding.sentence"),
        (f"Subtract 4 from both sides to get x = 6. [{P1}]", "grounding.number"),
        ("Subtract 4 from both sides. [PSG.MADE.UP]", "grounding.citation"),
        (f"Divide both sides by 4. [{P1}]", "meaning.term"),
        (f"Do not do the inverse operation to both sides. [{P1}]", "meaning.term"),
        (f"Add 4 to both sides. [{P1}]", "meaning.term"),
        ("NOT_IN_BOOK", "abstain"),
        ("", "schema.empty"),
    ],
)
def test_an_unsupported_answer_is_refused_with_the_rule_that_broke(reply: str, code: str) -> None:
    checked = run_checks(_ctx(), reply)
    assert not checked.ok and checked.code == code, (reply, checked.code)


def test_a_term_is_checked_against_the_passage_the_sentence_cites() -> None:
    # "divide" is in P2 but the sentence cites P1: the meaning term is not supported there.
    assert run_checks(_ctx(), f"Divide both sides by that number. [{P1}]").code == "meaning.term"
    ok = run_checks(_ctx(), f"Divide both sides by that number. [{P2}]")
    assert ok.ok, ok.code


def test_a_number_must_be_in_the_cited_passage_not_just_somewhere_in_the_source() -> None:
    reply = f"For 3x = 12, divide both sides by 3 to get x = 4. [{P1}]"  # numbers are in P2
    assert run_checks(_ctx(), reply).code == "grounding.number"


def test_citations_do_not_count_toward_the_word_limit() -> None:
    reply = " ".join(f"Subtract 4 from both sides. [{P1}]" for _ in range(1))
    assert run_checks(_ctx(), reply).ok
