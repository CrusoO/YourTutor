from __future__ import annotations

import uuid

from app.learner.bktf import AttemptKind
from app.learner.bktf_shadow import ShadowStep
from app.player.shadow_report import (
    MEANINGFUL_LOG_LOSS_DIFF,
    MIN_ATTEMPTS_TO_JUDGE,
    MIN_MEANINGFUL_GAP_DAYS,
    format_report,
    main,
)

STUDENT = uuid.UUID("12345678-1234-5678-1234-567812345678")


def step(
    n: int,
    *,
    kind: AttemptKind = AttemptKind.VALID,
    gap: float = 0.0,
    live: float = 0.5,
    shadow: float = 0.5,
    correct: bool = True,
    skill: str = "S1",
) -> ShadowStep:
    return ShadowStep(
        index=n,
        skill_id=skill,
        item_id=f"i{n}",
        kind=kind,
        correct=correct,
        gap_days=gap,
        predicted_live=live,
        predicted_shadow=shadow,
        p_live=0.4,
        p_shadow=0.45,
    )


def test_empty_log_says_so() -> None:
    assert "No logged practice attempts" in format_report(STUDENT, [])


def test_a_short_log_is_not_judged() -> None:
    text = format_report(STUDENT, [step(n) for n in range(5)])
    assert f"under {MIN_ATTEMPTS_TO_JUDGE}" in text
    assert "predicted these answers better" not in text


def test_shadow_win_is_reported_with_a_caveat() -> None:
    steps = [step(n, gap=3.0, live=0.3, shadow=0.9) for n in range(MIN_ATTEMPTS_TO_JUDGE)]
    text = format_report(STUDENT, steps)
    assert "BKT-F predicted these answers better" in text
    assert "One student is not enough" in text
    assert "forgetting was not exercised" not in text


def test_shadow_loss_is_reported() -> None:
    steps = [step(n, gap=3.0, live=0.9, shadow=0.3) for n in range(MIN_ATTEMPTS_TO_JUDGE)]
    assert "did not predict these answers better" in format_report(STUDENT, steps)


def test_zero_gaps_are_flagged() -> None:
    text = format_report(STUDENT, [step(n) for n in range(MIN_ATTEMPTS_TO_JUDGE)])
    assert "forgetting was not exercised" in text


def test_gaps_of_a_few_seconds_are_flagged_like_zero_gaps() -> None:
    seconds = 5 / 86_400
    steps = [step(n, gap=seconds) for n in range(MIN_ATTEMPTS_TO_JUDGE)]
    assert "forgetting was not exercised" in format_report(STUDENT, steps)


def test_one_long_gap_is_enough_to_stop_the_warning() -> None:
    steps = [step(n) for n in range(MIN_ATTEMPTS_TO_JUDGE)]
    steps.append(step(99, gap=MIN_MEANINGFUL_GAP_DAYS))
    assert "forgetting was not exercised" not in format_report(STUDENT, steps)


def test_a_tiny_difference_is_called_a_tie() -> None:
    near = 0.5 + MEANINGFUL_LOG_LOSS_DIFF / 100
    steps = [step(n, gap=3.0, live=0.5, shadow=near) for n in range(MIN_ATTEMPTS_TO_JUDGE)]
    text = format_report(STUDENT, steps)
    assert "No meaningful difference" in text
    assert "did not predict" not in text


def test_per_skill_counts() -> None:
    steps = [
        step(0, kind=AttemptKind.RAPID_GUESS),
        step(1, kind=AttemptKind.HINTED),
        step(2, skill="S2"),
    ]
    rows = format_report(STUDENT, steps).splitlines()
    s1 = next(line for line in rows if line.startswith("S1"))
    assert s1.split()[1:4] == ["2", "1", "1"]
    assert any(line.startswith("S2") for line in rows)


def test_report_shows_the_id_and_no_names() -> None:
    assert str(STUDENT) in format_report(STUDENT, [step(0)])


def test_a_bad_student_id_is_rejected(capsys) -> None:
    assert main(["--student", "not-a-uuid"]) == 1
    assert "must be a uuid" in capsys.readouterr().err
