"""Dev-only HTTP surface for the preview tools: a 404 unless DEV_TOOLS and ALLOW_DRAFT_CONTENT."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth.deps import DbSession
from app.config import settings
from app.db.models import StudentRow
from app.dev.scenarios import PIN, SCENARIOS

API_ROOT = Path(__file__).resolve().parents[2]


def require_dev_tools() -> None:
    if not (settings.dev_tools and settings.allow_draft_content):
        raise HTTPException(status_code=404, detail="not found")


router = APIRouter(prefix="/dev", dependencies=[Depends(require_dev_tools)], tags=["dev"])


@router.post("/seed")
def reseed() -> dict[str, Any]:
    """Re-create every scenario. Runs the CLI in a subprocess: replaying history pins the clock,
    which must never happen inside the process that is serving requests."""
    done = subprocess.run(
        [sys.executable, "-m", "app.dev", "seed_scenarios"],
        cwd=str(API_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if done.returncode != 0:
        raise HTTPException(status_code=500, detail=(done.stderr or done.stdout).strip())
    return {"ok": True, "output": done.stdout}


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
