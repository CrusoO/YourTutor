from __future__ import annotations

from fastapi import HTTPException

from app.config import settings


def require_research_module() -> None:
    if not settings.research_module:
        raise HTTPException(status_code=404, detail="not found")
