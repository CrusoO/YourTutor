"""Preview scenarios: students in known states, built by replaying events through the real engine.

Nothing here writes mastery or ladder rows. Each scenario replays what a student would do (answers,
lesson steps, session ends) through `apply_player_event`, with the clock set in the past so the
history looks like it happened before today, then lets the engine derive every state.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.actor import Actor
from app.auth.security import hash_pin
from app.config import settings
from app.db.models import ItemRow, OverlayRow, StudentRow, UserRow
from app.db.session import session_factory
from app.dev.clock import frozen
from app.dev.readers import card_due, ladder_levels
from app.player.runtime import _overlay_skills, apply_player_event, session_view
from app.registries.loaders import load_all_curricula

PIN = "1234"
EMAIL_PREFIX = "scenario."
EMAIL_DOMAIN = "@preview.local"
STEP = timedelta(seconds=20)  # time between replayed events
SESSION_GAP = timedelta(hours=2)
IDLE_MS = 11 * 60 * 1000


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    title: str
    description: str
    family_code: str
    first_name: str
    days_ago: int = 1  # where the replayed history starts, relative to now


SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        "new_student",
        "New student",
        "Just enrolled: no sessions, no mastery. Today shows the first-run state.",
        "DEVNEW",
        "Nima",
    ),
    ScenarioSpec(
        "mid_chapter",
        "Mid chapter",
        "Four skills at level 4, the fifth started, the rest untouched.",
        "DEVMID",
        "Mina",
    ),
    ScenarioSpec(
        "skill_at_level_4",
        "Skill at level 4",
        "Exactly the first skill reached level 4; an open session can be resumed.",
        "DEVLV4",
        "Lena",
    ),
    ScenarioSpec(
        "review_due",
        "Review due",
        "First skill at level 4 and its review is overdue: the next session opens with a warm-up.",
        "DEVRVW",
        "Rhea",
        days_ago=30,
    ),
    ScenarioSpec(
        "all_skills_level_4",
        "All skills level 4",
        "Every skill in the chapter at level 4 (extension practice and chapter complete).",
        "DEVALL",
        "Alma",
    ),
)

Stop = Callable[[list[str], dict[str, int], dict[str, int]], bool]


def _stop_for(name: str) -> Stop | None:
    if name in {"skill_at_level_4", "review_due"}:
        return lambda skills, levels, attempts: levels.get(skills[0], 0) >= 4
    if name == "mid_chapter":
        return lambda skills, levels, attempts: (
            all(levels.get(s, 0) >= 4 for s in skills[:4])
            and attempts.get(skills[4], 0) >= 1
            and levels.get(skills[4], 0) < 4
        )
    if name == "all_skills_level_4":
        return lambda skills, levels, attempts: all(levels.get(s, 0) >= 4 for s in skills)
    return None


def seed_scenarios(
    database_url: str | None = None, *, only: list[str] | None = None
) -> list[dict[str, Any]]:
    if not settings.allow_draft_content:
        raise RuntimeError("seeding preview scenarios needs ALLOW_DRAFT_CONTENT=true (dev only)")
    wanted = [s for s in SCENARIOS if only is None or s.name in only]
    report: list[dict[str, Any]] = []
    with session_factory(database_url)() as db:
        if not db.scalar(select(func.count()).select_from(ItemRow)):
            raise RuntimeError(
                "no content in this database: run `alembic upgrade head` and "
                "`python -m app.content load ../../content/` first"
            )
        curriculum_id, chapter_id = _pick_chapter(db)
        for spec in wanted:
            report.append(_seed_one(db, spec, curriculum_id, chapter_id))
            db.commit()
    return report


def _pick_chapter(db: Session) -> tuple[str, str]:
    """A curriculum whose grade-9 chapter id is also an overlay id (what the runtime looks up)."""
    for curriculum in sorted(load_all_curricula().values(), key=lambda c: c.id):
        for book in curriculum.books:
            for chapter in book.chapters:
                has_overlay = db.get(OverlayRow, chapter.id) is not None
                if chapter.id == chapter.overlay_id and has_overlay:
                    return curriculum.id, chapter.id
    raise RuntimeError("no curriculum chapter with a loaded overlay; load content first")


def _seed_one(
    db: Session, spec: ScenarioSpec, curriculum_id: str, chapter_id: str
) -> dict[str, Any]:
    admin = Actor(role="admin")
    email = f"{EMAIL_PREFIX}{spec.name}{EMAIL_DOMAIN}"
    old = db.scalar(select(UserRow).where(UserRow.email == email))
    if old is not None:
        service.delete_family(db, admin, old.id)
        db.flush()
    start = datetime.now(UTC) - timedelta(days=spec.days_ago)
    with frozen(start):
        parent = UserRow(id=uuid.uuid4(), role="parent", email=email, locale="en", created_at=start)
        db.add(parent)
        db.flush()
        student = service.create_student(
            db,
            admin,
            display_name=spec.first_name,
            grade=9,
            board=curriculum_id,
            home_language="en",
            exam_language="en",
            parent_id=parent.id,
            current_chapter_id=chapter_id,
            family_code=spec.family_code,
        )
        student.pin_hash = hash_pin(PIN)
        service.grant_consent(
            db, admin, student.id, version="preview-v1", scopes=["tutoring"], paper_ref=None
        )
        db.commit()
    stop = _stop_for(spec.name)
    if stop is not None:
        _Replay(db, student, admin).run(stop, start)
    summary = _summary(db, student)
    if spec.name == "review_due":
        _require_overdue_card(db, student)
    return {
        "name": spec.name,
        "title": spec.title,
        "description": spec.description,
        "family_code": spec.family_code,
        "pin": PIN,
        "summary": summary,
    }


def _summary(db: Session, student: StudentRow) -> str:
    levels, _ = ladder_levels(db, student)
    done = sum(1 for level in levels.values() if level >= 4)
    return f"{done} skill(s) at level 4+, {len(levels)} started"


def _require_overdue_card(db: Session, student: StudentRow) -> None:
    due = card_due(db, student, _overlay_skills(db, student)[0])
    if due is None or due > datetime.now(UTC):
        raise RuntimeError(
            "review_due scenario: the review is not overdue; move days_ago further back"
        )


class _Replay:
    """Drives sessions like a student who always answers correctly."""

    def __init__(self, db: Session, student: StudentRow, admin: Actor) -> None:
        self.db = db
        self.student = student
        self.admin = admin
        self.clock = datetime.now(UTC)

    def _levels(self) -> tuple[dict[str, int], dict[str, int]]:
        self.db.expire_all()
        return ladder_levels(self.db, self.student)

    def run(
        self, stop: Stop, start: datetime, *, max_sessions: int = 20, max_events: int = 1500
    ) -> None:
        self.clock = start
        skills = list(_overlay_skills(self.db, self.student))
        events = 0
        for _ in range(max_sessions):
            with frozen(self.clock):
                row = service.start_session(self.db, self.admin, self.student.id, "practice")
                view = session_view(self.db, self.admin, row)
                self.db.commit()
            action = view["action"]
            while action["type"] != "end_session" and events < max_events:
                event_type, item_id, payload = self._next_event(action)
                action = self._send(row, event_type, item_id, payload)
                events += 1
                levels, attempts = self._levels()
                if stop(skills, levels, attempts):
                    self._end_idle(row)
                    return
            self.clock += SESSION_GAP
        raise RuntimeError("scenario replay did not reach its target state")

    def _next_event(self, action: dict[str, Any]) -> tuple[str, str | None, dict[str, Any]]:
        kind = action["type"]
        if kind == "predict":
            return "predict_response", None, {"response": "a guess"}
        if kind in {
            "worked_example",
            "explain_back_prompt",
            "explain_back_result",
            "reveal_solution",
        }:
            return "continue", None, {}
        if kind in {"show_item", "warmup_item", "similar_item", "hint"}:
            item = self.db.get(ItemRow, action["item_id"])
            assert item is not None
            return "answer", item.id, {"response": item.answer["sympy"], "latency_ms": 2000}
        raise RuntimeError(f"scenario replay met an unexpected action: {kind}")

    def _send(
        self, row: Any, event_type: str, item_id: str | None, payload: dict[str, Any]
    ) -> dict:
        self.clock += STEP
        with frozen(self.clock):
            result = apply_player_event(
                self.db,
                self.admin,
                row,
                client_event_id=uuid.uuid4(),
                event_type=event_type,
                item_id=item_id,
                payload=payload,
            )
            self.db.commit()
        return result["action"]

    def _end_idle(self, row: Any) -> None:
        self.clock += timedelta(minutes=12)
        self._send(row, "idle_nudge", None, {"idle_ms": IDLE_MS})
