"""GET /actions/rules: the words that mean a command, for the browser to match locally."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.actions.rules import build_rules

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/rules")
def action_rules(language: str = "en") -> dict[str, Any]:
    """A GET with no user text, like `/context/finder-rules`: typed words never come here."""
    return build_rules(language)
