"""Offline packs: everything a browser needs to run practice for one chapter without a network.

A pack holds the chapter's offline-verifiable practice items (with answers, so the browser can
check them), the skill graph and BKT parameters, the chapter's lessons, the student's mastery,
ladder and review-card state at download time, and a hash that the sync call echoes back so the
server can tell when the content changed in between. Items the browser cannot judge (symbolic
answers, anything needing the server's algebra) are left out and stay online-only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.content.gate import content_status_is_servable
from app.content.packs import item_is_offline_verifiable
from app.db.models import ItemRow, LessonRow, MisconceptionRow, StudentRow
from app.learner.types import LearnerState
from app.orchestrator.diagnostic import DONT_KNOW
from app.orchestrator.types import CatalogItem
from app.player.runtime import (
    _bkt_and_prereqs,
    _locale_value,
    _overlay_skills,
    limits_for_student,
    load_catalog,
    load_learner,
)
from app.registries.loaders import load_notation_profiles

PACK_VERSION = 1


def pack_catalog(session: Session, skills: tuple[str, ...]) -> tuple[CatalogItem, ...]:
    """The chapter's practice items a browser can mark on its own, in a stable order."""
    allow_draft = settings.allow_draft_content
    rows = {row.id: row for row in session.scalars(select(ItemRow)).all()}
    out: list[CatalogItem] = []
    for item in load_catalog(session, allow_draft=allow_draft):
        row = rows.get(item.id)
        if row is None or item.pool != "practice" or item.primary_skill not in skills:
            continue
        answer = row.answer if isinstance(row.answer, dict) else None
        if not item_is_offline_verifiable(item_type=item.type, answer=answer, verify=item.verify):
            continue
        out.append(item)
    return tuple(sorted(out, key=lambda i: i.id))


def item_json(item: CatalogItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "skill_ids": list(item.skill_ids),
        "difficulty": item.difficulty,
        "pool": item.pool,
        "status": item.status,
        "role": item.role,
        "structure": item.structure,
        "type": item.type,
        "answer_sympy": item.answer_sympy,
        "accept": list(item.accept),
        "hints": [[level, text] for level, text in item.hints],
        "solution_steps": list(item.solution_steps),
        "misconception_rules": [[mid, list(vals)] for mid, vals in item.misconception_rules],
        "prediction_prompt": item.prediction_prompt,
        "authored_explanation": item.authored_explanation,
        "options": [dict(o) for o in item.options],
        "last_shown_at": None,
        "slip_patterns": [dict(p) for p in item.slip_patterns],
        "prereq_signatures": [dict(p) for p in item.prereq_signatures],
        "intermediate_values": list(item.intermediate_values),
        "min_plausible_ms": item.min_plausible_ms,
        "step_hints": list(item.step_hints),
        "hint_restate": item.hint_restate,
    }


def learner_json(learner: LearnerState) -> dict[str, Any]:
    return {
        "mastery": {
            sid: {
                "p_known": m.p_known,
                "attempts": m.attempts,
                "unhinted_correct": m.unhinted_correct,
                "hinted_correct": m.hinted_correct,
            }
            for sid, m in sorted(learner.mastery.items())
        },
        "ladders": {sid: row.to_json() for sid, row in sorted(learner.ladders.items())},
        "cards": {
            sid: {"due_at": c.due_at.isoformat(), "fsrs_state": c.fsrs_state}
            for sid, c in sorted(learner.cards.items())
        },
    }


def js_number(value: float) -> str:
    """A float written the way JavaScript's `JSON.stringify` writes it (1.0 is `1`, no `1e-05`)."""
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("not a finite number")
    if value == int(value) and abs(value) < 1e21:
        return str(int(value))
    text = repr(value)
    if "e" not in text:
        return text
    mantissa, exponent = text.split("e")
    exp = int(exponent)
    digits = mantissa.replace(".", "").replace("-", "")
    sign = "-" if value < 0 else ""
    if -6 <= exp < 21:
        if exp < 0:
            return f"{sign}0.{'0' * (-exp - 1)}{digits}"
        return f"{sign}{digits.ljust(exp + 1, '0')}"
    lead = f"{digits[0]}.{digits[1:]}" if len(digits) > 1 else digits
    return f"{sign}{lead}e{'+' if exp > 0 else '-'}{abs(exp)}"


def canonical(value: Any) -> str:
    """Canonical JSON: sorted keys, no spaces, numbers as JavaScript prints them, so the same
    data hashes to the same bytes in Python and in the browser."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return js_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        return (
            "{"
            + ",".join(f"{json.dumps(str(k), ensure_ascii=False)}:{canonical(v)}" for k, v in items)
            + "}"
        )
    raise TypeError(f"cannot write {type(value).__name__}")


def content_hash(catalog: list[dict[str, Any]], overlay: list[str], params: dict[str, Any]) -> str:
    blob = canonical({"catalog": catalog, "overlay": overlay, "params": params})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_pack(session: Session, student: StudentRow) -> dict[str, Any]:
    skills = _overlay_skills(session, student)
    params, prereqs = _bkt_and_prereqs(session, skills)
    locale = student.home_language or "en"
    stems = {row.id: _locale_value(row.stem, locale) for row in session.scalars(select(ItemRow))}
    catalog = [{**item_json(i), "stem": stems.get(i.id, "")} for i in pack_catalog(session, skills)]
    bkt = {
        sid: {
            "p_init": p.p_init,
            "p_learn": p.p_learn,
            "p_slip": p.p_slip,
            "p_guess": p.p_guess,
        }
        for sid, p in sorted(params.items())
    }
    remedial: dict[str, str] = {}
    texts: dict[str, str] = {}
    for mc in session.scalars(select(MisconceptionRow)):
        remedial[mc.id] = mc.remedial_skill
        text = _locale_value(mc.explanation, locale)
        if text:
            texts[mc.id] = text
    lessons = []
    for row in session.scalars(select(LessonRow).where(LessonRow.skill_id.in_(skills))):
        if content_status_is_servable(row.status, allow_draft=settings.allow_draft_content):
            lessons.append(
                {
                    "id": row.id,
                    "skill_id": row.skill_id,
                    "title": row.title,
                    "source_ref": row.source_ref,
                    "status": row.status,
                    "beats": row.beats,
                }
            )
    limits = limits_for_student(student)
    profile = load_notation_profiles().get("default_ascii")
    return {
        "version": PACK_VERSION,
        "generated_at": now_utc().isoformat(),
        "student_id": str(student.id),
        "chapter_id": (student.context_key or {}).get("chapter_id") or student.current_chapter_id,
        "hash": content_hash(catalog, list(skills), bkt),
        "overlay": list(skills),
        "prerequisites": {sid: list(prereqs.get(sid, ())) for sid in skills},
        "bkt_params": bkt,
        "misconception_remedial": remedial,
        "misconception_text": texts,
        "catalog": catalog,
        "lessons": lessons,
        "learner": learner_json(load_learner(session, student.id)),
        "limits": {
            "soft_active_ms": limits.soft_active_ms,
            "soft_item_cap": limits.soft_items,
            "hard_active_ms": limits.hard_active_ms,
            "max_words": limits.max_words,
        },
        "notation": {
            "decimal_separator": profile.decimal_separator if profile else ".",
            "multiply_symbols": list(profile.multiply_symbols) if profile else ["*"],
            "divide_symbols": list(profile.divide_symbols) if profile else ["/"],
        },
        "dont_know": sorted(DONT_KNOW),
    }
