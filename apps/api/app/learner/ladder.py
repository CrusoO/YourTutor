"""Mastery ladder (ARCHITECTURE §11.2): pure evidence rules, no I/O.

`apply_ladder_event` is the incremental step the policy uses; `compute` folds the same step over a
log (running BKT with the shared mastery service), so incremental and recompute cannot diverge.

Levels
  1 Understood           lesson flow done + the first practice item afterwards answered correctly
  2 Explained            an unhinted-correct first attempt on an `explain` item
  3 Solves with support  any correct answer on a `procedure` item (hints allowed)
  4 Solves independently p_known >= 0.95 and 3 consecutive unhinted-correct first attempts
                         (procedure/apply/transfer items) over >= 2 stem structures
  5 Applies              unhinted-correct first attempt on an `apply` item after level 4
  6 Transfers            unhinted-correct first attempt on a `transfer` item after level 5
  7 Retains              warm-up review correct >= 7 days after the last practice, then another
                         >= 21 days after the last practice (needs level 6); an incorrect review
                         resets retention and drops 7 -> 6

Levels 1-4 are earned independently; 5-7 chain. Explain-back grades, diagnostic and checkpoint
answers are never ladder events.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.learner.bkt import BktParams

LADDER_POOLS = frozenset({"practice", "warmup"})
STREAK_ROLES = frozenset({"procedure", "apply", "transfer"})
MASTERY_P = 0.95
STREAK_LENGTH = 3
MIN_STRUCTURES = 2
RETAIN_FIRST = timedelta(days=7)
RETAIN_SECOND = timedelta(days=21)
MAX_LEVEL = 7
STRETCH_DELAY = timedelta(days=1)  # first stretch item one day after the level was reached
STRETCH_LEVELS = (4, 5)  # level 4 -> an apply item, level 5 -> a transfer item
T_LEVEL = 4  # T = first overlay skill with ladder level below this

KIND_ANSWER = "answer"
KIND_HINT = "request_hint"
KIND_LESSON = "lesson_complete"
KIND_TEST_OUT = "test_out"  # skip ahead passed (ARCHITECTURE §9.7)


@dataclass(frozen=True)
class LadderEvent:
    event_id: str
    skill_id: str
    kind: str
    at: datetime
    item_id: str = ""
    correct: bool | None = None
    pool: str = "practice"
    role: str = "procedure"
    structure: str = ""


@dataclass
class SkillLadder:
    skill_id: str
    achieved: list[int] = field(default_factory=list)
    evidence: dict[int, list[str]] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    # memory carried between events
    seen: list[str] = field(default_factory=list)
    hinted: list[str] = field(default_factory=list)
    lesson_done: bool = False
    post_lesson_item: str | None = None
    last_practice_at: datetime | None = None
    run: list[tuple[str, str]] = field(default_factory=list)  # (event_id, structure)
    retention_events: list[str] = field(default_factory=list)

    @property
    def level(self) -> int:
        return max(self.achieved, default=0)

    @property
    def retention_stage(self) -> int:
        return int(self.flags.get("retention_stage", 0))

    def summary(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "evidence": {str(k): list(v) for k, v in sorted(self.evidence.items())},
            "flags": dict(sorted(self.flags.items())),
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "achieved": sorted(self.achieved),
            "evidence": {str(k): list(v) for k, v in sorted(self.evidence.items())},
            "flags": dict(self.flags),
            "seen": list(self.seen),
            "hinted": list(self.hinted),
            "lesson_done": self.lesson_done,
            "post_lesson_item": self.post_lesson_item,
            "last_practice_at": self.last_practice_at.isoformat()
            if self.last_practice_at
            else None,
            "run": [list(pair) for pair in self.run],
            "retention_events": list(self.retention_events),
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> SkillLadder:
        last = data.get("last_practice_at")
        return cls(
            skill_id=str(data["skill_id"]),
            achieved=[int(v) for v in data.get("achieved") or []],
            evidence={int(k): list(v) for k, v in (data.get("evidence") or {}).items()},
            flags=dict(data.get("flags") or {}),
            seen=list(data.get("seen") or []),
            hinted=list(data.get("hinted") or []),
            lesson_done=bool(data.get("lesson_done")),
            post_lesson_item=data.get("post_lesson_item"),
            last_practice_at=datetime.fromisoformat(last) if last else None,
            run=[(str(a), str(b)) for a, b in data.get("run") or []],
            retention_events=list(data.get("retention_events") or []),
        )


def _achieve(
    ladder: SkillLadder, level: int, event_ids: list[str], at: datetime | None = None
) -> None:
    if level not in ladder.achieved:
        ladder.achieved.append(level)
        ladder.evidence[level] = list(event_ids)
        key = f"stretch_after_{level}"
        if at is not None and level in STRETCH_LEVELS and key not in ladder.flags:
            ladder.flags[key] = (at + STRETCH_DELAY).isoformat()  # the stretch slot (G2a)


def lesson_level1_reached(ladder: SkillLadder, event: LadderEvent) -> bool:
    """The single seam for level 1 evidence.

    Until lessons exist (G3): the PREDICT -> WORKED_EXAMPLE flow was completed for the skill and
    the first practice item afterwards is answered correctly (hints allowed). G3 replaces this
    with lesson completion plus the lesson check item; nothing else in this module changes.
    """
    return (
        ladder.lesson_done
        and event.kind == KIND_ANSWER
        and bool(event.correct)
        and ladder.post_lesson_item == event.item_id
    )


def apply_ladder_event(
    ladders: dict[str, SkillLadder], event: LadderEvent, p_known: float
) -> SkillLadder | None:
    """Incremental update. `p_known` is the skill's value after BKT handled this event."""
    if event.kind == KIND_TEST_OUT:
        ladder = ladders.setdefault(event.skill_id, SkillLadder(skill_id=event.skill_id))
        if 4 not in ladder.achieved:
            _achieve(ladder, 4, [event.event_id], event.at)
            ladder.flags["evidence"] = "test_out"
        return ladder
    if event.kind != KIND_LESSON and event.pool not in LADDER_POOLS:
        return None
    ladder = ladders.setdefault(event.skill_id, SkillLadder(skill_id=event.skill_id))
    if event.kind == KIND_LESSON:
        ladder.lesson_done = True
        ladder.post_lesson_item = None
        return ladder
    if event.kind not in {KIND_ANSWER, KIND_HINT}:
        return ladder

    first = event.item_id not in ladder.seen
    previous_practice = ladder.last_practice_at
    achieved_before = set(ladder.achieved)

    if ladder.lesson_done and ladder.post_lesson_item is None:
        ladder.post_lesson_item = event.item_id
    if first:
        ladder.seen.append(event.item_id)
        if event.kind == KIND_HINT:
            ladder.hinted.append(event.item_id)
    unhinted_correct_first = (
        first and event.kind == KIND_ANSWER and bool(event.correct)
    )  # a hint request is the first event on a hinted item, so it never gets here

    if first:
        _first_attempt(ladder, event, p_known, unhinted_correct_first, achieved_before)
    if event.kind == KIND_ANSWER and event.correct:
        if event.role == "procedure":
            _achieve(ladder, 3, [event.event_id])
        if lesson_level1_reached(ladder, event):
            _achieve(ladder, 1, [event.event_id])
    if first and event.pool == "warmup":
        _review(ladder, event, previous_practice, review_correct=unhinted_correct_first)
    ladder.last_practice_at = event.at
    _retention_level(ladder)
    return ladder


def _first_attempt(
    ladder: SkillLadder,
    event: LadderEvent,
    p_known: float,
    unhinted_correct: bool,
    achieved_before: set[int],
) -> None:
    if unhinted_correct and event.role == "explain":
        _achieve(ladder, 2, [event.event_id])
    if unhinted_correct and event.role == "apply" and 4 in achieved_before:
        _achieve(ladder, 5, [event.event_id], event.at)
    if unhinted_correct and event.role == "transfer" and 5 in achieved_before:
        _achieve(ladder, 6, [event.event_id])
    if event.role in STREAK_ROLES:
        if unhinted_correct:
            ladder.run = [*ladder.run, (event.event_id, event.structure)][-STREAK_LENGTH:]
        else:
            ladder.run = []
    if (
        unhinted_correct
        and event.role in STREAK_ROLES
        and len(ladder.run) == STREAK_LENGTH
        and len({structure for _id, structure in ladder.run}) >= MIN_STRUCTURES
        and p_known >= MASTERY_P
    ):
        _achieve(ladder, 4, [event_id for event_id, _s in ladder.run], event.at)


def _review(
    ladder: SkillLadder,
    event: LadderEvent,
    previous_practice: datetime | None,
    *,
    review_correct: bool,
) -> None:
    stage = ladder.retention_stage
    if not review_correct:
        ladder.flags["retention_stage"] = 0
        ladder.retention_events = []
        if 7 in ladder.achieved:
            ladder.achieved.remove(7)
            ladder.evidence.pop(7, None)
            ladder.flags["lapsed"] = True
        return
    if previous_practice is None:
        return
    gap = event.at - previous_practice
    if stage == 0 and gap >= RETAIN_FIRST:
        ladder.flags["retention_stage"] = 1
        ladder.retention_events = [event.event_id]
    elif stage == 1 and gap >= RETAIN_SECOND:
        ladder.flags["retention_stage"] = 2
        ladder.retention_events = [*ladder.retention_events, event.event_id]


def _retention_level(ladder: SkillLadder) -> None:
    if ladder.retention_stage >= 2 and 6 in ladder.achieved and 7 not in ladder.achieved:
        _achieve(ladder, 7, ladder.retention_events)
        ladder.flags.pop("lapsed", None)


def compute(
    events: Iterable[LadderEvent],
    now: datetime,
    params_by_skill: Mapping[str, BktParams] | None = None,
) -> dict[str, SkillLadder]:
    """Fold the log into per-skill ladders. Events dated after `now` are ignored.

    BKT runs through the shared mastery service so `p_known` follows the same one-update-per-item
    rule as the live policy.
    """
    from app.learner.mastery_service import apply_event
    from app.learner.types import LearnerEvent, LearnerState

    default = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
    params = dict(params_by_skill or {})
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
        if event.at > now:
            continue
        if event.kind in {KIND_LESSON, KIND_TEST_OUT}:
            apply_ladder_event(ladders, event, p_known=0.0)
            continue
        if event.pool in LADDER_POOLS and event.kind in {KIND_ANSWER, KIND_HINT}:
            skill_params = params.setdefault(event.skill_id, default)
            apply_event(
                state,
                LearnerEvent(
                    item_id=event.item_id,
                    skill_id=event.skill_id,
                    event_type=event.kind,
                    correct=event.correct,
                    pool=event.pool,
                    session_id="",
                    is_warmup=event.pool == "warmup",
                ),
                {event.skill_id: skill_params},
                memory=memory,
            )
            p_known = state.mastery[event.skill_id].p_known
        else:
            p_known = 0.0
        apply_ladder_event(ladders, event, p_known)
    return ladders
