from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.learner.ladder import SkillLadder


@dataclass
class Mastery:
    skill_id: str
    p_known: float
    attempts: int = 0
    unhinted_correct: int = 0
    hinted_correct: int = 0

    @property
    def mastered(self) -> bool:
        return self.p_known >= 0.95 and self.unhinted_correct >= 3


@dataclass
class ReviewCard:
    skill_id: str
    due_at: datetime
    fsrs_state: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LearnerEvent:
    item_id: str
    skill_id: str
    event_type: str
    correct: bool | None = None
    pool: str = "practice"
    session_id: str = ""
    latency_ms: int | None = None
    is_warmup: bool = False


@dataclass
class LearnerState:
    mastery: dict[str, Mastery] = field(default_factory=dict)
    cards: dict[str, ReviewCard] = field(default_factory=dict)
    ladders: dict[str, SkillLadder] = field(default_factory=dict)

    def snapshot(self) -> dict:
        return {
            "mastery": {
                sid: {
                    "p_known": m.p_known,
                    "attempts": m.attempts,
                    "unhinted_correct": m.unhinted_correct,
                    "hinted_correct": m.hinted_correct,
                    "mastered": m.mastered,
                }
                for sid, m in sorted(self.mastery.items())
            },
            "cards": {
                sid: {"due_at": c.due_at.isoformat(), "fsrs_state": c.fsrs_state}
                for sid, c in sorted(self.cards.items())
            },
            "ladders": {sid: row.summary() for sid, row in sorted(self.ladders.items())},
        }
