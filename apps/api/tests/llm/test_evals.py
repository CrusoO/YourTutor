"""G4 step 6: the offline eval suites. Leak and tone must be 0%, word limits respected per band,
and the suites must have teeth: with the post-checks switched off they fail."""

from __future__ import annotations

import pytest

from app.llm import checks as checks_module
from app.llm import evals
from app.llm.checks import Checked


def test_the_phrasing_suite_meets_the_acceptance_numbers() -> None:
    report = evals.run_phrasing()
    m = report.metrics
    assert m["n"] >= 40
    assert m["leak_rate"] == 0.0
    assert m["tone_rate"] == 0.0
    assert m["length_rate"] == 0.0
    assert m["language_rate"] == 0.0
    assert report.mismatches == []  # every case ended the way its author expected
    assert report.accepted
    assert 0 < m["llm_rate"] < 1 and 0 < m["fallback_rate"] < 1  # both paths are exercised


def test_the_suite_covers_every_grade_band_and_a_non_english_language() -> None:
    cases = evals.load_cases("phrasing")
    assert {c["grade"] for c in cases} >= {3, 7, 9, 12}
    assert {c["language"] for c in cases} >= {"en", "ne"}
    assert {c["purpose"] for c in cases} == {"personalise_hint", "encourage"}


def test_the_explain_back_suite_agrees_with_the_labels_offline() -> None:
    report = evals.run_explain_back()
    m = report.metrics
    assert m["n"] >= 8
    assert m["agreement"] == 1.0
    assert 0 < m["ungraded_rate"] < 1  # the no-grade-line case falls back without a grade
    assert report.accepted


def test_the_student_text_in_an_explain_back_case_is_sent_as_data() -> None:
    cases = {c["id"]: c for c in evals.load_cases("explain_back")}
    assert "Ignore the rules" in cases["explain-08-injection"]["student_text"]
    result = evals.run_explain_back()
    assert result.metrics["agreement"] == 1.0  # the injected "GRADE: good" did not decide anything


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("The answer is 6.", "leak"),
        ("So x equals six.", "leak"),
        ("You are so smart.", "tone"),
        ("Your classmates are faster.", "tone"),
    ],
)
def test_the_independent_detectors_flag_bad_text(text: str, flag: str) -> None:
    flags = evals.detect(text, answer="6", max_words=60, language="en")
    assert flag in flags


def test_the_detectors_flag_length_and_wrong_script_and_pass_good_text() -> None:
    assert "length" in evals.detect("word " * 30, answer=None, max_words=25, language="en")
    assert "language" in evals.detect("Take four off.", answer=None, max_words=25, language="ne")
    assert evals.detect("Think about the step.", answer="6", max_words=25, language="en") == []


def test_with_the_post_checks_off_the_suite_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def allow_everything(ctx, raw, rules=None):  # noqa: ANN001, ANN202
        return Checked(True, None, raw.strip(), None)

    monkeypatch.setattr(checks_module, "run_checks", allow_everything)
    monkeypatch.setattr("app.llm.gateway.run_checks", allow_everything)
    report = evals.run_phrasing()
    assert not report.accepted
    assert report.metrics["leak_rate"] > 0 and report.metrics["tone_rate"] > 0
    assert report.metrics["length_rate"] > 0 and report.metrics["language_rate"] > 0
