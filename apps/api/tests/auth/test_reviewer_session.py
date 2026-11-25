"""A reviewer stays signed in longer than other roles (no new code every day)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.auth.service import issue_auth_token
from app.config import settings
from app.db.models import AuthSessionRow


def _lifetime_seconds(db: Session, role: str) -> float:
    issue_auth_token(db, role=role)
    db.flush()
    row = db.scalars(
        select(AuthSessionRow)
        .where(AuthSessionRow.role == role)
        .order_by(AuthSessionRow.created_at.desc())
    ).first()
    assert row is not None
    return (as_utc(row.expires_at) - as_utc(row.created_at)).total_seconds()


def test_a_reviewer_session_lasts_the_reviewer_setting(db: Session) -> None:
    assert abs(_lifetime_seconds(db, "reviewer") - settings.reviewer_session_ttl_seconds) < 5
    assert settings.reviewer_session_ttl_seconds == 7 * 86_400


def test_other_roles_keep_the_normal_session_length(db: Session) -> None:
    for role in ("teacher", "admin", "parent"):
        assert abs(_lifetime_seconds(db, role) - settings.session_ttl_seconds) < 5
    assert settings.session_ttl_seconds == 86_400
