"""Clear the typed question out of old video jobs.

The video prompt used to be kept in `video_jobs.request_json`. It is now kept only until the worker
starts the job. This removes the text from every existing row; settings and topic ids stay.

Revision ID: 0030_clear_video_prompts
Revises: 0029_lesson_records
Create Date: 2026-11-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_clear_video_prompts"
down_revision: str | None = "0029_lesson_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def clear_prompts(bind: sa.engine.Connection) -> int:
    """Drop the `prompt` key from every video job request. Returns how many rows changed."""
    if "video_jobs" not in set(sa.inspect(bind).get_table_names()):
        return 0
    jobs = sa.table("video_jobs", sa.column("id", sa.Uuid()), sa.column("request_json", sa.JSON()))
    changed = 0
    for row_id, request in bind.execute(sa.select(jobs.c.id, jobs.c.request_json)).all():
        if isinstance(request, dict) and "prompt" in request:
            kept = {k: v for k, v in request.items() if k != "prompt"}
            bind.execute(sa.update(jobs).where(jobs.c.id == row_id).values(request_json=kept))
            changed += 1
    return changed


def upgrade() -> None:
    clear_prompts(op.get_bind())


def downgrade() -> None:
    """The deleted text cannot come back."""
