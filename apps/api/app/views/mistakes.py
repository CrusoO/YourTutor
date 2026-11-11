"""The class mistake list and the warm-up built from it (teacher view, aggregate only).

Privacy shape (DPDP, learners are minors): the output is counts only. No student name or id ever
leaves this module. A row is shown only when at least K_FLOOR different students made that mistake,
and the whole list is withheld until at least K_FLOOR students were active in the window, so a
teacher cannot work out who made a mistake. The warm-up is built only from rows that already
passed the floor, so it cannot reveal a suppressed one either.

The aggregation and the warm-up choice are pure functions over plain records. The two functions at
the bottom read the database and call them. No model is called anywhere here: every word shown is
authored content.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.content.gate import content_status_is_servable
from app.db.models import (
    ChapterRow,
    ItemRow,
    MisconceptionHitRow,
    MisconceptionRow,
    OverlayRow,
    SessionRow,
    SkillRow,
)
from app.registries.locale_resolve import pick_localized_field

# k-anonymity floor. A mistake row needs this many different students, and a class needs this many
# active students, before anything is shown. A tunable default, not a decided value: counsel and
# the owner confirm it (see the PR description).
K_FLOOR = 5
DEFAULT_WINDOW_DAYS = 14
MAX_WINDOW_DAYS = 90
MAX_ROWS = 10
WARMUP_SIZE = 5
WARMUP_TARGETS = 3
# Practice and diagnostic items only; checkpoint items are kept back for measurement.
WARMUP_POOLS = frozenset({"practice", "diagnostic"})


@dataclass(frozen=True)
class Hit:
    """One wrong answer that matched a known misconception. `student` is only ever counted."""

    student: str
    misconception_id: str
    skill_id: str
    item_id: str
    at: datetime


@dataclass(frozen=True)
class Mistake:
    misconception_id: str
    students: int
    occurrences: int
    skill_id: str
    example_item_id: str


@dataclass(frozen=True)
class WarmItem:
    """An existing item, already checked as servable, with the misconceptions its options name."""

    id: str
    skill_id: str
    misconception_ids: frozenset[str]


def _modal(values: Iterable[str]) -> str:
    """Most common value; ties go to the smallest, so the result never depends on input order."""
    counts = Counter(values)
    return min(counts, key=lambda v: (-counts[v], v))


def aggregate(
    hits: Sequence[Hit], now: datetime, days: int = DEFAULT_WINDOW_DAYS, k: int = K_FLOOR
) -> list[Mistake]:
    """Misconceptions seen in the last `days` days, by how many students made them.

    Rows with fewer than `k` students are dropped. Order: most students, then most occurrences,
    then id, so equal rows are stable.
    """
    since = now - timedelta(days=days)
    inside = [h for h in hits if since <= h.at <= now]
    by_id: dict[str, list[Hit]] = {}
    for hit in inside:
        by_id.setdefault(hit.misconception_id, []).append(hit)
    rows = [
        Mistake(
            misconception_id=mid,
            students=len({h.student for h in group}),
            occurrences=len(group),
            skill_id=_modal(h.skill_id for h in group),
            example_item_id=_modal(h.item_id for h in group),
        )
        for mid, group in by_id.items()
    ]
    kept = [r for r in rows if r.students >= k]
    kept.sort(key=lambda r: (-r.students, -r.occurrences, r.misconception_id))
    return kept[:MAX_ROWS]


def enough_students(active: int, k: int = K_FLOOR) -> bool:
    return active >= k


def _rank(seed: str, target: str, item_id: str) -> str:
    return hashlib.sha256(f"{seed}|{target}|{item_id}".encode()).hexdigest()


def pick_warmup(
    items: Sequence[WarmItem], targets: Sequence[str], seed: str, size: int = WARMUP_SIZE
) -> list[tuple[str, str]]:
    """(item id, misconception id) pairs for the warm-up, from existing items only.

    Items are taken in turn, one per target, so the top mistake does not crowd out the others. The
    order inside a target is a seeded hash, so the same seed always gives the same warm-up and a
    new seed gives a different one. An item is used once. If the items run out the list is shorter
    than `size`; it is never padded.
    """
    queues: dict[str, list[str]] = {}
    for t in targets:
        ids = [i.id for i in items if t in i.misconception_ids]
        queues[t] = sorted(ids, key=lambda x: _rank(seed, t, x))
    chosen: list[tuple[str, str]] = []
    used: set[str] = set()
    progressed = True
    while len(chosen) < size and progressed:
        progressed = False
        for target in targets:
            queue = queues[target]
            while queue and queue[0] in used:
                queue.pop(0)
            if queue and len(chosen) < size:
                item_id = queue.pop(0)
                used.add(item_id)
                chosen.append((item_id, target))
                progressed = True
    return chosen


# ── database side ─────────────────────────────────────────────────────────────────────────────


def _active_students(db: Session, visible: set[uuid.UUID], since: datetime) -> int:
    if not visible:
        return 0
    rows = db.scalars(
        select(SessionRow.student_id)
        .where(SessionRow.student_id.in_(visible), SessionRow.last_active_at >= since)
        .distinct()
    ).all()
    return len(rows)


def _hits(
    db: Session, visible: set[uuid.UUID], since: datetime, now: datetime
) -> tuple[list[Hit], dict[str, ItemRow]]:
    rows = db.execute(
        select(MisconceptionHitRow, ItemRow)
        .join(ItemRow, ItemRow.id == MisconceptionHitRow.item_id)
        .where(MisconceptionHitRow.student_id.in_(visible), MisconceptionHitRow.created_at >= since)
    ).all()
    hits = [
        Hit(
            student=str(hit.student_id),
            misconception_id=hit.misconception_id,
            skill_id=item.primary_skill,
            item_id=item.id,
            at=as_utc(hit.created_at),
        )
        for hit, item in rows
        if as_utc(hit.created_at) <= now
    ]
    return hits, {item.id: item for _, item in rows}


def _chapter_title(db: Session, skill_id: str) -> str:
    for overlay in db.scalars(select(OverlayRow)).all():
        if skill_id in (overlay.skill_ids or []):
            chapter = db.scalar(select(ChapterRow).where(ChapterRow.overlay_id == overlay.id))
            title = pick_localized_field(dict(chapter.titles or {}), "en") if chapter else ""
            return title or overlay.chapter
    return ""


def _steps(item: ItemRow) -> list[str]:
    return [str((s or {}).get("en") or "") for s in item.solution_steps or []]


def _example(item: ItemRow | None, allow_draft: bool) -> dict[str, Any] | None:
    """The authored right working of one item, only if that item is servable."""
    if item is None or not content_status_is_servable(item.status, allow_draft=allow_draft):
        return None
    steps = [s for s in _steps(item) if s]
    if not steps:
        return None
    return {"item_id": item.id, "stem": str((item.stem or {}).get("en") or ""), "steps": steps}


def mistake_list(
    db: Session,
    visible: set[uuid.UUID],
    now: datetime,
    days: int,
    allow_draft: bool,
) -> dict[str, Any]:
    """Counts only. `visible` is already limited to the teacher's own class and shared students."""
    since = now - timedelta(days=days)
    active = _active_students(db, visible, since)
    base: dict[str, Any] = {
        "kind": "mistakes",
        "window_days": days,
        "minimum_students": K_FLOOR,
    }
    if not enough_students(active):
        return {**base, "state": "not_enough_students", "mistakes": []}
    hits, items = _hits(db, visible, since, now)
    rows = aggregate(hits, now, days)
    labels = {
        m.id: m
        for m in db.scalars(
            select(MisconceptionRow).where(
                MisconceptionRow.id.in_([r.misconception_id for r in rows])
            )
        )
    }
    skills = {
        s.id: pick_localized_field(dict(s.title or {}), "en") or s.id
        for s in db.scalars(select(SkillRow).where(SkillRow.id.in_([r.skill_id for r in rows])))
    }
    out = []
    for row in rows:
        mc = labels.get(row.misconception_id)
        out.append(
            {
                "misconception_id": row.misconception_id,
                "label": pick_localized_field(dict(mc.title or {}), "en") if mc else "",
                "explanation": pick_localized_field(dict(mc.explanation or {}), "en") if mc else "",
                "students": row.students,
                "occurrences": row.occurrences,
                "skill_id": row.skill_id,
                "skill_title": skills.get(row.skill_id, row.skill_id),
                "chapter": _chapter_title(db, row.skill_id),
                "example": _example(items.get(row.example_item_id), allow_draft),
            }
        )
    return {**base, "state": "ok" if out else "none", "mistakes": out}


def _warm_items(
    db: Session, targets: Sequence[str], allow_draft: bool
) -> tuple[list[WarmItem], dict[str, ItemRow]]:
    """Servable practice or diagnostic items with a rule for a target, whose rule names at least
    one wrong answer (an answer other than the right one)."""
    wanted = set(targets)
    found: list[WarmItem] = []
    rows: dict[str, ItemRow] = {}
    for row in db.scalars(select(ItemRow).where(ItemRow.pool.in_(WARMUP_POOLS))):
        if not content_status_is_servable(row.status, allow_draft=allow_draft):
            continue
        right = str((row.answer or {}).get("sympy") or "")
        named = {
            str(rule.get("id"))
            for rule in row.misconception_rules or []
            if any(str(a) != right for a in rule.get("when_answer_equals") or [])
        } & wanted
        if named and _steps(row):
            found.append(WarmItem(row.id, row.primary_skill, frozenset(named)))
            rows[row.id] = row
    return found, rows


def warmup(
    db: Session,
    visible: set[uuid.UUID],
    now: datetime,
    days: int,
    seed: str,
    allow_draft: bool,
) -> dict[str, Any]:
    """A warm-up from the class's top mistakes, from existing servable items only."""
    listing = mistake_list(db, visible, now, days, allow_draft)
    base: dict[str, Any] = {
        "kind": "warmup",
        "window_days": days,
        "seed": seed,
        "size": WARMUP_SIZE,
        "items": [],
        "short_by": WARMUP_SIZE,
    }
    if listing["state"] != "ok":
        return {**base, "state": listing["state"], "targets": []}
    top = listing["mistakes"][:WARMUP_TARGETS]
    targets = [m["misconception_id"] for m in top]
    label = {m["misconception_id"]: m["label"] for m in top}
    pool, rows = _warm_items(db, targets, allow_draft)
    picked = pick_warmup(pool, targets, seed)
    skills = {
        s.id: pick_localized_field(dict(s.title or {}), "en") or s.id
        for s in db.scalars(
            select(SkillRow).where(SkillRow.id.in_({r.primary_skill for r in rows.values()}))
        )
    }
    items: list[dict[str, Any]] = []
    for item_id, target in picked:
        row = rows[item_id]
        right = str((row.answer or {}).get("sympy") or "")
        options = [
            {"id": str(o.get("id")), "text": str(o.get("en") or "")} for o in row.options or []
        ]
        answer_text = next((o["text"] for o in options if o["id"] == right), right)
        items.append(
            {
                "item_id": row.id,
                "skill_title": skills.get(row.primary_skill, row.primary_skill),
                "stem": str((row.stem or {}).get("en") or ""),
                "options": options,
                "answer": answer_text,
                "steps": [s for s in _steps(row) if s],
                "targets": {"misconception_id": target, "label": label[target]},
            }
        )
    short = WARMUP_SIZE - len(items)
    served = {target for _, target in picked}
    unserved = [t for t in targets if t not in served]
    return {
        **base,
        "state": "ok" if items else "no_items",
        "items": items,
        "short_by": short,
        "unserved": [{"misconception_id": t, "label": label[t]} for t in unserved],
        "targets": [{"misconception_id": t, "label": label[t]} for t in targets],
    }
