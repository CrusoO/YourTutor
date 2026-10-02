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
    diagnostic_results: list[tuple[str, str, bool]] = field(default_factory=list)
    last_event: Event | None = None
    stored_explain_text: str | None = None
    similar_from_item_id: str | None = None
    last_wrong_response: str | None = None
    bkt_memory: dict = field(default_factory=lambda: {
        "bkt_done": set(),
        "hinted": set(),
        "first_wrong": set(),
        "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
        "warmup_skills": set(),
    })

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
