from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.learner.bkt import BktParams
from app.learner.types import LearnerState

SOFT_ACTIVE_MS = 15 * 60 * 1000
HARD_ACTIVE_MS = 20 * 60 * 1000
IDLE_END_MS = 10 * 60 * 1000
LATENCY_CAP_MS = 5 * 60 * 1000
SOFT_ITEM_CAP = 12
DIAG_ITEM_CAP = 16
DIAG_ACTIVE_MS = 15 * 60 * 1000
LOW_PRIOR = 0.05
MAX_WARMUP = 3
PREREQ_BELOW = 0.6
MASTERY_P = 0.95


@dataclass(frozen=True)
class CatalogItem:
    id: str
    skill_ids: tuple[str, ...]
    difficulty: float
    pool: str
    status: str
    role: str = "procedure"
    structure: str = ""
    type: str = "expression"
    answer_sympy: str = "0"
    accept: tuple[str, ...] = ()
    hints: tuple[tuple[int, str], ...] = ()
    solution_steps: tuple[str, ...] = ()
    misconception_rules: tuple[tuple[str, tuple[str, ...]], ...] = ()
    prediction_prompt: str = ""
    authored_explanation: str = ""
    verify: str | dict[str, Any] | None = None
    options: tuple[dict[str, Any], ...] = ()
    last_shown_at: datetime | None = None
    # diagnosis fields (G2): authored, optional
    slip_patterns: tuple[dict[str, Any], ...] = ()
    prereq_signatures: tuple[dict[str, Any], ...] = ()
    intermediate_values: tuple[str, ...] = ()
    min_plausible_ms: int | None = None
    step_hints: tuple[str, ...] = ()
    hint_restate: str = ""

    @property
    def primary_skill(self) -> str:
        return self.skill_ids[0]

    def hint(self, level: int) -> str:
        for row_level, text in self.hints:
            if row_level == level:
                return text
        return ""


@dataclass
class Event:
    type: str
    response: str | None = None
    client_correct: bool | None = None
    latency_ms: int | None = None
    item_id: str | None = None
    idle_ms: int | None = None
    text: str | None = None
    event_id: str | None = None


@dataclass
class Action:
    type: str
    item_id: str | None = None
    skill_id: str | None = None
    hint_level: int | None = None
    misconception_id: str | None = None
    text: str | None = None
    source: str = "authored"
    correct: bool | None = None
    grade: str | None = None
    store_text: bool = False
    llm_called: bool = False
    ended_reason: str | None = None
    resumable: bool = False
    guardrail_flag: str | None = None
    rejected: bool = False
    state_before: str | None = None
    state_after: str | None = None
    rule_id: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    session_type: str
    now: datetime
    catalog: tuple[CatalogItem, ...]
    overlay_skill_ids: tuple[str, ...]
    bkt_params: dict[str, BktParams]
    prerequisites: dict[str, tuple[str, ...]] = field(default_factory=dict)
    phase: str = "start"
    current_skill: str | None = None
    current_item_id: str | None = None
    hint_level_shown: int = 0
    attempt_after_hint2: bool = False
    bkt_updated: set[str] = field(default_factory=set)
    explain_back_done: set[str] = field(default_factory=set)
    introduced_skills: set[str] = field(default_factory=set)
    shown_item_ids: list[str] = field(default_factory=list)
    items_completed: int = 0
    active_ms: int = 0
    last_active_at: datetime | None = None
    warmup_done: bool = False
    warmup_left: int = 0
    last_action: Action | None = None
    consent_revoked: bool = False
    has_ai_processing: bool = False
    has_api_key: bool = False
    allow_draft: bool = False
    llm_called: bool = False
    ended_reason: str | None = None
    diagnostic_ids: list[str] = field(default_factory=list)
    checkpoint_ids: list[str] = field(default_factory=list)
    sequence_index: int = 0
    diagnostic_results: list[dict] = field(default_factory=list)
    skipped_skills: set[str] = field(default_factory=set)
    skills_not_tested: list[str] = field(default_factory=list)
    checkpoint_answers: list[dict] = field(default_factory=list)
    checkpoint_result: dict | None = None
    last_event: Event | None = None
    last_correct: bool | None = None
    event_counter: int = 0
    session_key: str = ""  # stable id (the DB session id) for per-session FSRS aggregates
    stored_explain_text: str | None = None
    similar_from_item_id: str | None = None
    last_wrong_response: str | None = None
    last_wrong_item_id: str | None = None  # first attempt on an item = this differs from the item
    fast_streak: int = 0  # consecutive answers faster than the item's min_plausible_ms (R35)
    help_without_attempt: int = 0  # help opened before any attempt (R35)
    misconception_remedial: dict[str, str] = field(default_factory=dict)  # misconception -> skill
    last_diagnosis: dict[str, Any] | None = None  # stored on the event as payload.diagnosis
    misconception_text: dict[str, str] = field(default_factory=dict)  # id -> authored hint
    stuck_item_id: str | None = None  # the picker is offered once per item (R32)
    stretch_served: int = 0  # stretch items served this session (max 2)
    # G2b: probe (R33) and wheel-spinning (R34)
    teacher_share: bool = False  # alerts are only queued with this consent scope
    alerts: list[dict[str, str]] = field(default_factory=list)  # drained by the runtime
    wheel_skills: set[str] = field(default_factory=set)
    wrong_first_streak: dict[str, int] = field(default_factory=dict)  # per skill
    skill_items: dict[str, int] = field(default_factory=dict)  # items seen per skill
    seen_items: set[str] = field(default_factory=set)
    answered_items: set[str] = field(default_factory=set)
    lesson_prereq_levels: dict[str, list[int]] = field(default_factory=dict)  # R38, by skill
    probe_for: str | None = None  # the target skill while a probe is running
    probe_skill: str | None = None  # the prerequisite being probed
    probe_done: set[str] = field(default_factory=set)  # one probe per prerequisite
    scheduled_prereq: str | None = None  # a prerequisite that comes next (R33)
    scheduled_left: int = 0
    # G2b: frustration, challenge, never-end-on-failure, praise
    reveals: int = 0  # reveals since the last step-down (R36)
    wrong_run: int = 0  # consecutive wrong first attempts across skills (R36)
    tier_down_items: int = 0  # items still to serve one tier lower (R36)
    tier_up_next: bool = False  # the next item is one tier higher (R37)
    unhinted_run: int = 0  # consecutive unhinted correct first attempts (R37)
    last_failure: bool = False  # the last answered item ended in a miss (R40)
    win_served: bool = False  # the one likely-success item before a cap-end (R40)
    skill_failed: set[str] = field(default_factory=set)  # failed, not yet recovered
    last_praise_at: int = -99  # items_completed when encouragement last appeared
    praise_count: int = 0
    # session limits from the student's grade band (defaults: the 9-10 band)
    soft_active_ms: int = SOFT_ACTIVE_MS
    soft_item_cap: int = SOFT_ITEM_CAP
    hard_active_ms: int = HARD_ACTIVE_MS
    max_words: int = 60  # per tutor message
    stretch_skills: set[str] = field(default_factory=set)  # one stretch per skill per session
    blocked_skills: set[str] = field(default_factory=set)
    content_gaps: list[dict[str, Any]] = field(default_factory=list)
    bkt_memory: dict = field(
        default_factory=lambda: {
            "bkt_done": set(),
            "hinted": set(),
            "first_wrong": set(),
            "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
            "warmup_skills": set(),
        }
    )

    def item(self, item_id: str | None = None) -> CatalogItem | None:
        target = item_id or self.current_item_id
        if target is None:
            return None
        for row in self.catalog:
            if row.id == target:
                return row
        return None


def default_params() -> BktParams:
    return BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)


def empty_learner() -> LearnerState:
    return LearnerState()
