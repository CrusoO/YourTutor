"""Dev-only HTTP surface for the preview tools: a 404 unless DEV_TOOLS and ALLOW_DRAFT_CONTENT."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import DbSession
from app.config import settings
from app.db.models import StudentRow
from app.dev.scenarios import PIN, SCENARIOS
from app.lessons.loader import all_lessons, lesson_by_id
from app.lessons.widgets import verify_widget_result

API_ROOT = Path(__file__).resolve().parents[2]


def require_dev_tools() -> None:
    if not (settings.dev_tools and settings.allow_draft_content):
        raise HTTPException(status_code=404, detail="not found")


router = APIRouter(prefix="/dev", dependencies=[Depends(require_dev_tools)], tags=["dev"])


@router.post("/seed")
def reseed(only: list[str] | None = Query(default=None)) -> dict[str, Any]:
    """Re-create every scenario (or only the named ones: `?only=slip_prone`). Runs the CLI in a
    subprocess: replaying history pins the clock, which must never happen inside the process that
    is serving requests."""
    names = {s.name for s in SCENARIOS}
    unknown = [name for name in only or [] if name not in names]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown scenario: {unknown[0]}")
    flags = [arg for name in only or [] for arg in ("--only", name)]
    done = subprocess.run(
        [sys.executable, "-m", "app.dev", "seed_scenarios", *flags],
        cwd=str(API_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if done.returncode != 0:
        raise HTTPException(status_code=500, detail=(done.stderr or done.stdout).strip())
    return {"ok": True, "output": done.stdout}


class WidgetVerifyIn(BaseModel):
    lesson_id: str
    widget_id: str
    final_state: Any = None


@router.get("/lessons")
def list_lessons() -> dict[str, Any]:
    return {
        "lessons": [
            {
                "id": lesson.id,
                "skill_id": lesson.skill_id,
                "title": lesson.title.en,
                "source_ref": lesson.source_ref,
                "status": lesson.status.value,
                "beats": [beat.kind for beat in lesson.beats],
            }
            for lesson in all_lessons()
        ]
    }


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: str) -> dict[str, Any]:
    lesson = lesson_by_id(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    return lesson.model_dump(mode="json", by_alias=True, exclude_none=True)


@router.post("/widgets/verify")
def verify_widget(body: WidgetVerifyIn) -> dict[str, Any]:
    """Stateless server check of a widget result, for the login-free lesson preview."""
    lesson = lesson_by_id(body.lesson_id)
    widget = (
        next((w for w in lesson.widgets() if w.widget_id == body.widget_id), None)
        if lesson
        else None
    )
    if widget is None:
        return {"ok": False, "code": "widget_unknown"}
    ok, code = verify_widget_result(
        widget, {"widget_id": body.widget_id, "final_state": body.final_state}
    )
    return {"ok": ok, "code": code}


@router.get("/items/{item_id}/answer")
def item_answer(item_id: str, db: DbSession) -> dict[str, Any]:
    """The authored answer, so the UI tests can type a correct response. Dev only."""
    from app.db.models import ItemRow

    row = db.get(ItemRow, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="item not found")
    answer = row.answer or {}
    return {"id": row.id, "answer": answer.get("sympy"), "accept": list(answer.get("accept") or [])}


@router.get("/scenarios")
def list_scenarios(db: DbSession) -> dict[str, Any]:
    codes = set(
        db.scalars(
            select(StudentRow.family_code).where(
                StudentRow.family_code.in_([s.family_code for s in SCENARIOS])
            )
        ).all()
    )
    return {
        "scenarios": [
            {
                "name": s.name,
                "title": s.title,
                "description": s.description,
                "family_code": s.family_code,
                "pin": PIN,
                "seeded": s.family_code in codes,
            }
            for s in SCENARIOS
        ]
    }
