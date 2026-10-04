from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.learner.bkt import BktParams
from app.learner.ladder import (
    KIND_ANSWER,
    KIND_HINT,
    KIND_LESSON,
    LadderEvent,
    SkillLadder,
    apply_ladder_event,
    compute,
)
from app.learner.mastery_service import apply_event
from app.learner.types import LearnerEvent, LearnerState

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
NOW = T0 + timedelta(days=36500)
SKILL = "S1"
FAST = BktParams(p_init=0.2, p_learn=0.5, p_slip=0.05, p_guess=0.1)
SLOW = BktParams(p_init=0.1, p_learn=0.01, p_slip=0.1, p_guess=0.4)


class Log:
    """Builds ladder events with auto ids and an advancing clock."""

    def __init__(self, skill: str = SKILL) -> None:
        self.skill = skill
        self.events: list[LadderEvent] = []
        self.clock = T0

    def add(
        self,
        kind: str,
        item: str = "",
        *,
        correct: bool | None = None,
        role: str = "procedure",
        structure: str = "s-a",
        pool: str = "practice",
        after: timedelta = timedelta(minutes=1),
    ) -> LadderEvent:
        self.clock = self.clock + after
        event = LadderEvent(
            event_id=f"e{len(self.events) + 1}",
            skill_id=self.skill,
            kind=kind,
            at=self.clock,
            item_id=item,
            correct=correct,
            pool=pool,
            role=role,
            structure=structure,
        )
        self.events.append(event)
        return event

    def right(self, item: str, **kw) -> LadderEvent:
        return self.add(KIND_ANSWER, item, correct=True, **kw)

    def wrong(self, item: str, **kw) -> LadderEvent:
        return self.add(KIND_ANSWER, item, correct=False, **kw)

    def hint(self, item: str, **kw) -> LadderEvent:
        return self.add(KIND_HINT, item, **kw)

    def lesson(self, **kw) -> LadderEvent:
        return self.add(KIND_LESSON, **kw)

    def ladder(self, params: BktParams = FAST) -> SkillLadder:
        return compute(self.events, NOW, {self.skill: params}).get(
            self.skill, SkillLadder(skill_id=self.skill)
        )


def streak(log: Log, structures: list[str], start: int = 1) -> None:
    for offset, structure in enumerate(structures):
        log.right(f"i{start + offset}", structure=structure)


# --- level 1 ---------------------------------------------------------------------------


def test_level1_needs_lesson_and_correct_first_item_after_it() -> None:
    log = Log()
    log.lesson()
    log.right("i1", role="recall")
    ladder = log.ladder()
    assert ladder.level == 1
    assert ladder.evidence[1] == ["e2"]


def test_level1_allows_hints_on_that_first_item() -> None:
    log = Log()
    log.lesson()
    log.wrong("i1", role="recall")
    log.hint("i1", role="recall")
    log.right("i1", role="recall")
    assert log.ladder().level == 1


def test_level1_not_earned_when_first_item_never_correct() -> None:
    log = Log()
    log.lesson()
    log.wrong("i1", role="recall")  # revealed, never correct
    log.right("i2", role="recall")  # a later item does not count
    assert log.ladder().level == 0


def test_level1_not_earned_without_the_lesson_flow() -> None:
    log = Log()
    log.right("i1", role="recall")
    assert log.ladder().level == 0


# --- levels 2 and 3 ----------------------------------------------------------------------


def test_level2_needs_unhinted_correct_explain_item() -> None:
    log = Log()
    log.right("x1", role="explain")
    ladder = log.ladder()
    assert ladder.level == 2 and ladder.evidence[2] == ["e1"]


def test_level2_not_from_hinted_or_retried_explain_item() -> None:
    hinted = Log()
    hinted.hint("x1", role="explain")
    hinted.right("x1", role="explain")
    assert hinted.ladder().level == 0
    retried = Log()
    retried.wrong("x1", role="explain")
    retried.right("x1", role="explain")
    assert retried.ladder().level == 0


def test_level2_not_from_other_roles() -> None:
    log = Log()
    for index, role in enumerate(["recall", "apply", "transfer"]):
        log.right(f"i{index}", role=role)
    assert 2 not in log.ladder().achieved


def test_level3_from_any_correct_procedure_even_with_hints() -> None:
    log = Log()
    log.hint("p1")
    log.right("p1")
    ladder = log.ladder()
    assert ladder.level == 3 and ladder.evidence[3] == ["e2"]


# --- level 4 ---------------------------------------------------------------------------


def test_level4_needs_streak_over_two_structures_and_mastery() -> None:
    log = Log()
    streak(log, ["s-a", "s-b", "s-a"])
    ladder = log.ladder()
    assert ladder.level == 4
    assert ladder.evidence[4] == ["e1", "e2", "e3"]


def test_single_structure_streak_never_reaches_level4() -> None:
    log = Log()
    streak(log, ["s-a"] * 6)
    ladder = log.ladder()
    assert ladder.level == 3 and 4 not in ladder.achieved


def test_hinted_correct_answers_never_reach_level4() -> None:
    log = Log()
    for index, structure in enumerate(["s-a", "s-b", "s-c", "s-d", "s-e"], start=1):
        log.hint(f"i{index}", structure=structure)
        log.right(f"i{index}", structure=structure)
    assert log.ladder().level == 3


def test_a_wrong_first_attempt_breaks_the_streak() -> None:
    log = Log()
    streak(log, ["s-a", "s-b"])
    log.wrong("i3", structure="s-c")
    log.right("i3", structure="s-c")  # retry is not a first attempt
    streak(log, ["s-d", "s-e"], start=4)
    assert log.ladder().level == 3
    log.right("i6", structure="s-f")
    assert log.ladder().level == 4


def test_level4_needs_p_known_at_least_point_95() -> None:
    log = Log()
    streak(log, ["s-a", "s-b", "s-c"])
    assert log.ladder(SLOW).level == 3
    assert log.ladder(FAST).level == 4


def test_recall_and_explain_items_do_not_extend_the_streak() -> None:
    log = Log()
    log.right("i1", structure="s-a")
    log.right("r1", role="recall", structure="s-b")
    log.right("x1", role="explain", structure="s-c")
    log.right("i2", structure="s-d")
    assert log.ladder().level == 3  # only two streak items so far
    log.right("i3", structure="s-e")
    assert log.ladder().level == 4


# --- levels 5 and 6 ------------------------------------------------------------------------


def _at_level4() -> Log:
    log = Log()
    streak(log, ["s-a", "s-b", "s-c"])
    return log


def test_level5_needs_unhinted_correct_apply_after_level4() -> None:
    log = _at_level4()
    log.right("a1", role="apply", structure="s-w")
    ladder = log.ladder()
    assert ladder.level == 5 and ladder.evidence[5] == ["e4"]


def test_apply_before_level4_does_not_count_for_level5() -> None:
    log = Log()
    log.right("a1", role="apply", structure="s-w")
    streak(log, ["s-a", "s-b", "s-c"], start=1)
    ladder = log.ladder()
    assert ladder.level == 4 and 5 not in ladder.achieved


def test_hinted_apply_does_not_reach_level5() -> None:
    log = _at_level4()
    log.hint("a1", role="apply", structure="s-w")
    log.right("a1", role="apply", structure="s-w")
    assert log.ladder().level == 4


def test_level6_needs_transfer_after_level5() -> None:
    log = _at_level4()
    log.right("t0", role="transfer", structure="s-t0")  # before level 5: does not count
    assert log.ladder().level == 4
    log.right("a1", role="apply", structure="s-w")
    log.right("t1", role="transfer", structure="s-t1")
    ladder = log.ladder()
    assert ladder.level == 6 and ladder.evidence[6] == [f"e{len(log.events)}"]


# --- level 7 and retention -----------------------------------------------------------------


def _at_level6() -> Log:
    log = _at_level4()
    log.right("a1", role="apply", structure="s-w")
    log.right("t1", role="transfer", structure="s-t1")
    return log


def _review(log: Log, item: str, days: int, *, correct: bool = True) -> LadderEvent:
    method = log.right if correct else log.wrong
    return method(item, pool="warmup", after=timedelta(days=days))


def test_level7_needs_reviews_after_7_and_then_21_days() -> None:
    log = _at_level6()
    first = _review(log, "p9", 8)
    assert log.ladder().level == 6
    second = _review(log, "p10", 22)
    ladder = log.ladder()
    assert ladder.level == 7
    assert ladder.evidence[7] == [first.event_id, second.event_id]


def test_review_that_comes_too_early_does_not_count() -> None:
    log = _at_level6()
    _review(log, "p9", 3)
    _review(log, "p10", 30)  # first counted review is this one (>= 7 days), stage 1 only
    ladder = log.ladder()
    assert ladder.level == 6 and ladder.retention_stage == 1


def test_second_review_before_21_days_does_not_complete_retention() -> None:
    log = _at_level6()
    _review(log, "p9", 8)
    _review(log, "p10", 10)
    assert log.ladder().level == 6
    _review(log, "p11", 25)
    assert log.ladder().level == 7


def test_incorrect_review_drops_7_to_6_and_resets_retention() -> None:
    log = _at_level6()
    _review(log, "p9", 8)
    _review(log, "p10", 22)
    assert log.ladder().level == 7
    _review(log, "p11", 30, correct=False)
    dropped = log.ladder()
    assert dropped.level == 6
    assert dropped.retention_stage == 0 and dropped.flags.get("lapsed") is True
    _review(log, "p12", 9)
    _review(log, "p13", 22)
    assert log.ladder().level == 7


def test_level7_needs_level6_first() -> None:
    log = _at_level4()
    _review(log, "p9", 8)
    _review(log, "p10", 22)
    ladder = log.ladder()
    assert ladder.level == 4 and ladder.retention_stage == 2
    log.right("a1", role="apply", structure="s-w")
    log.right("t1", role="transfer", structure="s-t1")
    assert log.ladder().level == 7


def test_hinted_review_counts_as_incorrect() -> None:
    log = _at_level6()
    _review(log, "p9", 8)
    log.hint("p10", pool="warmup", after=timedelta(days=22))
    assert log.ladder().retention_stage == 0


# --- events that must never move the ladder ---------------------------------------------


@pytest.mark.parametrize("pool", ["diagnostic", "checkpoint"])
def test_assessment_events_never_change_the_ladder(pool: str) -> None:
    log = Log()
    for index in range(1, 8):
        log.right(f"i{index}", role="explain", structure=f"s-{index}", pool=pool)
    assert compute(log.events, NOW, {SKILL: FAST}) == {}
    ladders: dict[str, SkillLadder] = {}
    assert apply_ladder_event(ladders, log.events[0], 0.99) is None
    assert ladders == {}


def test_unknown_event_kinds_such_as_explain_back_are_ignored() -> None:
    ladders: dict[str, SkillLadder] = {}
    event = LadderEvent(
        event_id="e1", skill_id=SKILL, kind="explain_back", at=T0, item_id="i1", correct=True
    )
    apply_ladder_event(ladders, event, 0.99)
    assert ladders[SKILL].level == 0 and ladders[SKILL].seen == []


def test_events_after_now_are_ignored() -> None:
    log = Log()
    streak(log, ["s-a", "s-b", "s-c"])
    early = compute(log.events, T0 + timedelta(minutes=2), {SKILL: FAST})[SKILL]
    assert early.level == 3
    assert compute(log.events, NOW, {SKILL: FAST})[SKILL].level == 4


def test_level_never_falls_except_retention_lapse() -> None:
    log = _at_level6()
    previous = 0
    for index in range(30):
        log.wrong(f"w{index}", structure=f"s-{index}")
        level = log.ladder().level
        assert level >= previous
        previous = level


# --- incremental == recompute ------------------------------------------------------------

ITEMS = {
    "i0": ("S1", "procedure", "sa"),
    "i1": ("S1", "procedure", "sb"),
    "i2": ("S1", "procedure", "sc"),
    "i3": ("S1", "explain", "sx"),
    "i4": ("S1", "apply", "sy"),
    "i5": ("S1", "transfer", "sz"),
    "j0": ("S2", "procedure", "ta"),
    "j1": ("S2", "procedure", "tb"),
    "j2": ("S2", "recall", "tr"),
    "j3": ("S2", "apply", "tc"),
}
GAPS = [timedelta(minutes=1), timedelta(hours=2), timedelta(days=8), timedelta(days=22)]
KINDS = [KIND_ANSWER] * 6 + [KIND_HINT, KIND_LESSON, "explain_back"]
POOLS = ["practice"] * 5 + ["warmup", "warmup", "diagnostic", "checkpoint"]


@st.composite
def event_logs(draw) -> list[LadderEvent]:
    count = draw(st.integers(min_value=0, max_value=60))
    clock = T0
    out: list[LadderEvent] = []
    for index in range(count):
        item = draw(st.sampled_from(sorted(ITEMS)))
        skill, role, structure = ITEMS[item]
        kind = draw(st.sampled_from(KINDS))
        pool = draw(st.sampled_from(POOLS))
        clock = clock + draw(st.sampled_from(GAPS))
        out.append(
            LadderEvent(
                event_id=f"e{index}",
                skill_id=skill,
                kind=kind,
                at=clock,
                item_id="" if kind == KIND_LESSON else item,
                correct=draw(st.booleans()) if kind == KIND_ANSWER else None,
                pool=pool,
                role=role,
                structure=structure,
            )
        )
    return out


def _incremental(
    events: list[LadderEvent], params: dict[str, BktParams], *, persist: bool
) -> dict[str, SkillLadder]:
    """Mirror the live policy: BKT first, then the ladder step; optionally round-trip JSON."""
    state = LearnerState()
    memory: dict = {
        "bkt_done": set(),
        "hinted": set(),
        "first_wrong": set(),
        "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
        "warmup_skills": set(),
    }
    ladders: dict[str, SkillLadder] = {}
    for event in events:
        p_known = 0.0
        if event.kind in {KIND_ANSWER, KIND_HINT} and event.pool in {"practice", "warmup"}:
            apply_event(
                state,
                LearnerEvent(
                    item_id=event.item_id,
                    skill_id=event.skill_id,
                    event_type=event.kind,
                    correct=event.correct,
                    pool=event.pool,
                    is_warmup=event.pool == "warmup",
                ),
                {event.skill_id: params[event.skill_id]},
                memory=memory,
            )
            p_known = state.mastery[event.skill_id].p_known
        apply_ladder_event(ladders, event, p_known)
        if persist:
            ladders = {sid: SkillLadder.from_json(row.to_json()) for sid, row in ladders.items()}
    return ladders


PARAMS = {"S1": FAST, "S2": BktParams(p_init=0.3, p_learn=0.3, p_slip=0.1, p_guess=0.2)}


def _json(ladders: dict[str, SkillLadder]) -> dict[str, dict]:
    return {sid: row.to_json() for sid, row in ladders.items()}


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(event_logs())
def test_recompute_equals_incremental_on_random_logs(events: list[LadderEvent]) -> None:
    recomputed = _json(compute(events, NOW, PARAMS))
    for persist in (False, True):
        assert _json(_incremental(events, PARAMS, persist=persist)) == recomputed


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(event_logs(), st.integers(min_value=0, max_value=60))
def test_every_prefix_matches_recompute(events: list[LadderEvent], cut: int) -> None:
    prefix = events[:cut]
    assert _json(compute(prefix, NOW, PARAMS)) == _json(_incremental(prefix, PARAMS, persist=True))


def test_json_round_trip_keeps_memory() -> None:
    log = _at_level6()
    ladder = log.ladder()
    again = SkillLadder.from_json(ladder.to_json())
    assert again.to_json() == ladder.to_json()
    assert again.level == 6
